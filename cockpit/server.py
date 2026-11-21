"""Synthetic-only judge profile and local casework prototype."""
from argparse import ArgumentParser
from collections import defaultdict
from email.parser import BytesParser
from email.policy import default
from getpass import getpass
from hashlib import scrypt, sha256
from hmac import compare_digest
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlsplit, unquote
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError
import os
import json
import re
import secrets
import time

from . import data, insights, intake, rules, ui, xlsx

ROOT = Path(__file__).resolve().parents[1]
TTL = 8*3600


def encode_password(password):
    salt = secrets.token_bytes(16)
    return salt.hex()+':'+scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1).hex()


def valid_password(encoded,password):
    salt,expected = encoded.split(':')
    actual = scrypt(password.encode(),salt=bytes.fromhex(salt),n=2**14,r=8,p=1).hex()
    return compare_digest(expected,actual)


def account(db,username,password,role,assignment=''):
    if not re.fullmatch(r'[a-zA-Z0-9._-]{2,40}',username) or len(password)<12 or len(password)>256:
        raise ValueError('Use a valid username and a password of 12–256 characters')
    if role=='worker' and not assignment:
        raise ValueError('Worker account requires an assignment')
    with db:
        db.execute('INSERT INTO accounts VALUES(?,?,?,?) ON CONFLICT(username) DO UPDATE SET password=excluded.password,role=excluded.role,assignment=excluded.assignment',
                   (username,encode_password(password),role,assignment))
        db.execute('DELETE FROM sessions WHERE username=?',(username,))


def digest(token):
    return sha256(token.encode()).hexdigest()


class App(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self,address,path,hosted):
        self.path = path
        self.hosted = hosted
        self.attempts = defaultdict(list)
        self.attempt_lock = Lock()
        self.dummy = encode_password(secrets.token_hex(24))
        super().__init__(address,Handler)

    def allow_login(self, client):
        now = time.monotonic()
        with self.attempt_lock:
            if len(self.attempts)>5000:
                self.attempts = defaultdict(list,{k:v for k,v in self.attempts.items() if v and now-v[-1]<60})
                if len(self.attempts)>5000 and client not in self.attempts:
                    return False
            attempts = [t for t in self.attempts[client] if now-t<60]
            self.attempts[client] = attempts
            if len(attempts)>=8:
                return False
            attempts.append(now)
            return True


class Handler(BaseHTTPRequestHandler):
    server_version = 'Cockpit'

    def log_message(self, *_):
        pass

    def cookie(self,key,value,age=None):
        secure = '; Secure' if self.server.hosted else ''
        expires = f'; Max-Age={age}' if age is not None else ''
        return f'{key}={value}; Path=/; HttpOnly; SameSite=Strict{secure}{expires}'

    def respond(self,status=200,body='',content='text/html; charset=utf-8',headers=()):
        if isinstance(body,str):
            body = body.encode()
        self.send_response(status)
        for k,v in [('Content-Type',content),('Content-Length',str(len(body))),('Cache-Control','no-store'),
                    ('X-Content-Type-Options','nosniff'),('Referrer-Policy','no-referrer'),
                    ('Content-Security-Policy',"default-src 'none'; style-src 'self'; img-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"),*headers]:
            self.send_header(k,v)
        self.end_headers()
        if body:
            self.wfile.write(body)

    def redirect(self,path='/',headers=()):
        self.respond(303,headers=[('Location',path),*headers])

    def page(self,key,body,status=200,headers=()):
        self.respond(status,ui.layout(self.lang,key,body,self.identity,self.csrf,self.snapshot),headers=headers)

    def form(self,limit):
        size = int(self.headers.get('Content-Length','0'))
        if not 0<size<=limit:
            raise ValueError('body_size')
        kind = self.headers.get('Content-Type','')
        raw = self.rfile.read(size)
        if kind.startswith('application/x-www-form-urlencoded'):
            return {k:v[0] for k,v in parse_qs(raw.decode(),max_num_fields=30).items()},[]
        if kind.startswith('multipart/form-data') and '\n' not in kind and '\r' not in kind:
            message = BytesParser(policy=default).parsebytes(b'Content-Type: '+kind.encode()+b'\r\n\r\n'+raw)
            fields,files = {},[]
            for part in message.iter_parts():
                name = part.get_param('name',header='content-disposition')
                if part.get_filename() is not None:
                    files.append((name,part.get_payload(decode=True)))
                elif name:
                    value = part.get_payload(decode=True)
                    if len(value)>512:
                        raise ValueError('field_size')
                    fields[name] = value.decode()
            return fields,files
        raise ValueError('content_type')

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch(True)

    def dispatch(self,post=False):
        self.connection.settimeout(15)
        url = urlsplit(self.path)
        path = url.path
        try:
            cookies = SimpleCookie(self.headers.get('Cookie',''))
        except CookieError:
            cookies = SimpleCookie()
        def cookie_value(name):
            return cookies[name].value if name in cookies else ''
        self.lang = ui.LOCALES.index(cookie_value('locale')) if cookie_value('locale') in ui.LOCALES else 0
        self.identity = self.snapshot = None
        self.csrf = ''
        if not post and path=='/favicon.ico':
            return self.respond(204)
        if not post and path=='/health':
            return self.respond(200,'ok','text/plain')
        if not post and path in ('/static/app.css','/static/bern.jpg'):
            asset = ROOT / path.lstrip('/')
            if asset.is_file():
                return self.respond(200,asset.read_bytes(),'text/css' if path.endswith('css') else 'image/jpeg')
            return self.respond(404)
        if not post and path.startswith('/language/') and path.split('/')[-1] in ui.LOCALES:
            # Restrict redirects to the four dashboard routes and sign-in.
            previous = '/'+parse_qs(url.query).get('view',[''])[0]
            if previous=='/case':
                previous='/queue'
            if previous not in ('/login','/overview','/queue','/reports','/ai','/forecast','/intake') and not re.fullmatch(r'/case/DEMO-[0-9]{5,}',previous):
                previous = '/'
            return self.redirect(previous,[('Set-Cookie',self.cookie('locale',path.split('/')[-1],31536000))])
        db = data.connect(self.server.path)
        try:
            token = cookie_value('sid')
            if re.fullmatch(r'[A-Za-z0-9_-]{40,60}',token):
                self.identity = db.execute('SELECT a.username,a.role,a.assignment,s.csrf,s.selected FROM sessions s JOIN accounts a USING(username) WHERE token=? AND expires>?',
                                           (digest(token),int(time.time()))).fetchone()
            if not self.identity:
                if path!='/login':
                    return self.redirect('/login')
                return self.signin(db,post,cookie_value('login_csrf'))
            auth = self.identity
            self.csrf = auth['csrf']
            role = auth['role']
            if path in ('/','/login') and not post:
                return self.redirect('/reports' if role=='importer' else '/overview')
            allowed = {
              'judge':{'overview','queue','case','reports','export','ai','forecast','forecast-upload','forecast-reset','intake','intake-save','seed','snapshot','import','logout'},
              'worker':{'overview','queue','case','reports','export','ai','intake','intake-save','snapshot','logout'},
              'manager':{'overview','reports','export','ai','forecast','forecast-upload','forecast-reset','snapshot','logout'},
              'importer':{'reports','intake','intake-save','ai','seed','snapshot','import','logout'},
            }
            route = path.split('/')[1]
            if route not in allowed[role] or (self.server.hosted and
                    (route in ('import','forecast-upload','forecast-reset','intake-save') or (route=='intake' and post))):
                return self.page('no_access',ui.heading(self.lang,'no_access'),403)
            mutations = {'logout','seed','snapshot','import','intake-save','forecast-upload','forecast-reset'}
            if (route in mutations and not post) or (post and route not in mutations|{'intake'}):
                return self.respond(405)
            query = {k:v[0] for k,v in parse_qs(url.query,max_num_fields=15).items()}
            if post:
                fields,files = self.form(40_000_000 if route=='import' else 2_300_000 if route=='intake' else 40_000 if route=='forecast-upload' else 8192)
                if not compare_digest(fields.get('csrf','').encode(),self.csrf.encode()):
                    return self.page('no_access',ui.heading(self.lang,'no_access'),403)
                if route=='logout':
                    with db:
                        db.execute('DELETE FROM sessions WHERE token=?',(digest(token),))
                    return self.redirect('/login',[('Set-Cookie',self.cookie('sid','',0))])
                if route in ('forecast-upload','forecast-reset'):
                    with db:
                        if route=='forecast-upload':
                            if len(files)!=1 or files[0][0]!='series':
                                raise ValueError('expected_series')
                            series = insights.read_aggregate_series(files[0][1])
                            db.execute('INSERT INTO forecast_input VALUES(?,?) ON CONFLICT(username) DO UPDATE SET series=excluded.series',
                                       (auth['username'],json.dumps(series)))
                        else:
                            db.execute('DELETE FROM forecast_input WHERE username=?',(auth['username'],))
                        db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',(route,'accepted'))
                    return self.redirect('/forecast')
                if route=='snapshot':
                    selected = int(fields.get('id','0'))
                    if db.execute('SELECT 1 FROM snapshots WHERE id=? AND (?=0 OR source="synthetic")',
                                  (selected,self.server.hosted)).fetchone():
                        self.select(db,token,selected)
                    return self.redirect('/reports')
                if route in ('import','seed'):
                    return self.import_snapshot(db,route,token,fields,files)
            if self.server.hosted:
                selection = auth['selected'] or db.execute('SELECT id FROM snapshots WHERE source="synthetic" ORDER BY asof DESC LIMIT 1').fetchone()
                selection = selection[0] if not isinstance(selection,int) and selection else selection
                self.snapshot,tables = data.get_snapshot(db,selection) if selection else (None,{})
                if self.snapshot and self.snapshot['source']!='synthetic':
                    self.snapshot,tables = None,{}
            else:
                self.snapshot,tables = data.get_snapshot(db,auth['selected'])
            if route=='reports':
                return self.show_reports(db,query.get('notice',''))
            if not self.snapshot:
                return self.page(route,ui.heading(self.lang,'empty'),404)
            cases = rules.evaluate(self.snapshot,tables) if role!='importer' else []
            if role=='worker':
                cases = [c for c in cases if c['worker']==auth['assignment']]
            if route=='overview':
                return self.page(route,ui.overview(self.lang,self.snapshot,cases,role=='manager',query.get('factor','age')))
            if route=='queue':
                return self.page(route,ui.queue(self.lang,cases,query.get('q','')[:64],max(1,int(query.get('page','1'))),query.get('state','')))
            if route=='case':
                identifier = unquote(path.split('/')[-1])
                case = next((c for c in cases if c['id']==identifier),None)
                return self.page('case',ui.detail(self.lang,case) if case else ui.heading(self.lang,'empty'),200 if case else 404)
            if route=='export':
                blob = xlsx.write(ui.export(self.lang,self.snapshot,cases,role))
                return self.respond(200,blob,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                    [('Content-Disposition','attachment; filename="cockpit.xlsx"')])
            if route=='ai':
                topic = query.get('topic','a1')
                answer = insights.gateway(insights.RuleQuestion(topic,self.lang))
                aggregate = insights.gateway(insights.AggregateQuestion('entry_cohort'),self.snapshot['asof'],cases) if role in ('judge','manager') and self.snapshot['source']=='synthetic' else None
                return self.page(route,ui.assistant(self.lang,topic,answer,aggregate))
            if route=='forecast':
                stored = db.execute('SELECT series FROM forecast_input WHERE username=?',(auth['username'],)).fetchone() if not self.server.hosted else None
                series = json.loads(stored[0]) if stored else None
                report = insights.backtest([r[1] for r in series] if series else None)
                return self.page(route,ui.forecast(self.lang,report,min(100000,max(0,int(query.get('rate','0')))),cases,
                                                   series,not self.server.hosted,self.csrf))
            if route in ('intake','intake-save'):
                return self.intake(db,route,post,fields if post else {},files if post else [],tables,cases)
            return self.respond(404)
        except (ValueError, OverflowError, BadZipFile, ParseError, KeyError, IndexError):
            return self.page('review',ui.heading(self.lang,'review'),400)
        finally:
            db.close()

    def signin(self,db,post,csrf):
        if not post:
            if not re.fullmatch(r'[A-Za-z0-9_-]{43}',csrf):
                csrf = secrets.token_urlsafe(32)
            return self.page('login',ui.login(self.lang,csrf),headers=[('Set-Cookie',self.cookie('login_csrf',csrf,600))])
        fields,_ = self.form(8192)
        valid_csrf = bool(csrf) and compare_digest(csrf.encode(),fields.get('csrf','').encode())
        if valid_csrf and self.server.allow_login(self.client_address[0]):
            username = fields.get('username','')[:80]
            password = fields.get('password','')
            row = db.execute('SELECT password FROM accounts WHERE username=?',(username,)).fetchone()
            if len(password)<=256 and valid_password(row['password'] if row else self.server.dummy,password) and row:
                token = secrets.token_urlsafe(32)
                with db:
                    db.execute('DELETE FROM sessions WHERE expires<=?',(int(time.time()),))
                    db.execute('INSERT INTO sessions VALUES(?,?,?,?,?)',(digest(token),username,secrets.token_urlsafe(32),int(time.time())+TTL,None))
                    db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('sign_in','success'))
                return self.redirect('/',[('Set-Cookie',self.cookie('sid',token,TTL)),('Set-Cookie',self.cookie('login_csrf','',0))])
        csrf = secrets.token_urlsafe(32)
        return self.page('login',ui.login(self.lang,csrf,'invalid_login'),401,[('Set-Cookie',self.cookie('login_csrf',csrf,600))])

    def select(self,db,token,selected):
        with db:
            db.execute('UPDATE sessions SET selected=? WHERE token=?',(selected,digest(token)))

    def show_reports(self,db,notice='',issues=(),status=200):
        history = db.execute('SELECT id,asof,source FROM snapshots WHERE (?=0 OR source="synthetic") ORDER BY asof DESC,id DESC',
                             (self.server.hosted,)).fetchall()
        return self.page('reports',ui.reports(self.lang,self.snapshot,history,self.identity['role'],self.csrf,self.server.hosted,notice,issues),status)

    def import_snapshot(self,db,route,token,fields,files):
        report = fields.get('date','')
        if route=='seed':
            if report not in data.MONTHS:
                raise ValueError('invalid_month')
            inputs = data.seed(report).values()
        else:
            inputs = [blob for name,blob in files if name=='workbooks']
            if len(inputs)!=11:
                raise ValueError('expected_11_workbooks')
        try:
            selected,repeated = data.load_files(db,inputs,report,'synthetic' if route=='seed' else 'local')
        except data.ImportFailure as exc:
            with db:
                db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('snapshot_import','rejected'))
            self.snapshot,_ = data.get_snapshot(db,self.identity['selected'])
            return self.show_reports(db,'rejected',exc.errors,422)
        self.select(db,token,selected)
        return self.redirect('/reports?notice='+('repeated' if repeated else 'uploaded'))

    def intake(self,db,route,post,fields,files,tables,cases):
        lang = self.lang
        esc = ui.esc
        text = ui.text
        role = self.identity['role']
        authorized = {c['id'] for c in cases}
        if role=='importer':
            authorized = {r['_person'] for r in tables['clients']}
        num_to_person = {r['Zemis Nummer']:r['_person'] for r in tables['clients'] if r['_person'] in authorized}
        if route=='intake-save':
            pid = fields.get('person')
            category = fields.get('category')
            if pid not in authorized or category not in insights.CATEGORIES:
                raise ValueError('invalid_approval')
            with db:
                db.execute('INSERT INTO intake VALUES(?,?,?) ON CONFLICT(snapshot,person) DO UPDATE SET category=excluded.category',
                           (self.snapshot['id'],pid,category))
                db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('intake_review','accepted'))
            return self.redirect('/intake')
        if self.server.hosted:
            result = insights.gateway(insights.IntakeQuestion('scheduling'))
            return self.page('intake',ui.heading(lang,'intake')+f'<section class="panel"><p>{text(lang,"synthetic_only")}</p><p>{text(lang,result["category"])}</p></section>')
        feedback = ''
        if post:
            if len(files)!=1 or files[0][0]!='report':
                raise ValueError('expected_pdf')
            result = intake.suggest(files[0][1],num_to_person)
            if result['mode']=='review':
                options = ''.join(f'<option value="{key}" {"selected" if key in result["suggestions"] else ""}>{text(lang,key)}</option>'
                                  for key in insights.CATEGORIES)
                feedback = ui.post('/intake-save',self.csrf,f'<p>{esc(result["person"])}</p>'
                    f'<input type="hidden" name="person" value="{esc(result["person"])}">'
                    f'<label>{text(lang,"category")} <select name="category">{options}</select></label>'+ui.action(lang,'review_save'))
            else:
                feedback = f'<p role="status">{text(lang,"manual")}</p>'
        saved = list(db.execute('SELECT person,category FROM intake WHERE snapshot=?',(self.snapshot['id'],)))
        if role=='importer':
            approvals = f'<p>{text(lang,"rows")} {len(saved)}</p>'
        else:
            approvals = ui.table(['ID',ui.tr(lang,'category')],((esc(r['person']),text(lang,r['category'])) for r in saved if r['person'] in authorized))
        form = ui.post('/intake',self.csrf,'<label>PDF <input type="file" name="report" accept=".pdf" required></label>'+ui.action(lang,'pdf_review'),True)
        return self.page('intake',ui.heading(lang,'intake')+f'<section class="panel">{form}{feedback}{approvals}</section>')


def main():
    os.umask(0o077)
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--db',default=os.getenv('COCKPIT_DB','runtime/cockpit.sqlite'))
    commands = parser.add_subparsers(dest='command',required=True)
    serve = commands.add_parser('serve')
    serve.add_argument('--bind',default='127.0.0.1')
    serve.add_argument('--port',type=int,default=int(os.getenv('PORT','8000')))
    serve.add_argument('--hosted',action='store_true')
    serve.add_argument('--demo',action='store_true',help='create a local judge account if none exists')
    bootstrap = commands.add_parser('account')
    bootstrap.add_argument('username')
    bootstrap.add_argument('role',choices=('judge','worker','manager','importer'))
    bootstrap.add_argument('--assignment',default='')
    commands.add_parser('seed')
    seeds = commands.add_parser('fixtures')
    seeds.add_argument('--output',default='runtime/fixtures')
    seeds.add_argument('--people',type=int,default=144)
    imp = commands.add_parser('import')
    imp.add_argument('date')
    imp.add_argument('workbooks',nargs=11)
    remove = commands.add_parser('delete-synthetic')
    remove.add_argument('id',type=int)
    args = parser.parse_args()
    if args.command=='fixtures':
        for month in data.MONTHS:
            directory = Path(args.output)/month
            directory.mkdir(exist_ok=True,parents=True)
            for key,blob in data.seed(month,args.people).items():
                (directory/data.SCHEMA[key]['template']).write_bytes(blob)
        return
    path = Path(args.db)
    path.parent.mkdir(exist_ok=True,parents=True)
    db = data.connect(path)
    if args.command=='account':
        account(db,args.username,os.getenv('COCKPIT_PASSWORD') or getpass(),args.role,args.assignment)
    elif args.command=='import':
        try:
            print(data.load_files(db,[Path(p).read_bytes() for p in args.workbooks],args.date,'local'))
        except data.ImportFailure as exc:
            for issue in exc.errors:
                print(*issue)
            raise SystemExit(1)
    elif args.command=='delete-synthetic':
        with db:
            deleted = db.execute('DELETE FROM snapshots WHERE source="synthetic" AND id=?',(args.id,)).rowcount
            if deleted:
                db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('snapshot_delete','accepted'))
        print(f'Snapshots deleted: {deleted}')
    elif args.command in ('serve','seed'):
        if args.command=='serve' and args.hosted and args.demo:
            parser.error('--demo cannot provision public accounts')
        if args.command=='serve' and not args.hosted and args.bind not in ('127.0.0.1','localhost','::1'):
            parser.error('A non-loopback bind requires --hosted')
        for month in data.MONTHS:
            if not db.execute('SELECT 1 FROM snapshots WHERE source="synthetic" AND asof=?',(month,)).fetchone():
                data.load_files(db,data.seed(month).values(),month,'synthetic')
        if args.command=='serve':
            if args.demo and not db.execute('SELECT 1 FROM accounts').fetchone():
                password = secrets.token_urlsafe(16)
                account(db,'judge',password,'judge')
                print('Local sign-in: judge / '+password,flush=True)
            if not db.execute('SELECT 1 FROM accounts').fetchone():
                parser.error('Provision a staff account with the account command first')
            db.close()
            print(f'Listening on {args.bind}:{args.port}',flush=True)
            with App((args.bind,args.port),path,args.hosted) as server:
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
            return
    db.close()


if __name__=='__main__':
    main()
