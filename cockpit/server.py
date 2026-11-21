"""Synthetic-only judge profile and local casework prototype."""
from argparse import ArgumentParser
from collections import defaultdict, OrderedDict
from contextlib import closing
from datetime import date
from email.parser import BytesParser
from email.policy import default
from getpass import getpass
from hashlib import scrypt, sha256
from hmac import compare_digest
from http.cookies import SimpleCookie, CookieError
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from urllib.parse import parse_qs, urlsplit, unquote, urlencode
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError
import os
import json
import re
import secrets
import time

from . import ai, data, insights, intake, predict, redact, rules, ui, xlsx

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
        self.model_lock = Lock()
        self.models = OrderedDict()
        self.ai_answers = {}
        with closing(data.connect(path)):
            pass
        super().__init__(address,Handler)

    def read_model(self,db,snapshot):
        def load():
            _, tables = data.get_snapshot(db,snapshot['id'])
            return tables,rules.evaluate(snapshot,tables)
        if snapshot['source']!='synthetic' or sum(json.loads(snapshot['inspected']).values())>30_000:
            return load()
        key = snapshot['id'],snapshot['digest']
        with self.model_lock:
            if key not in self.models:
                self.models[key] = load()
                if len(self.models)>3:
                    self.models.popitem(last=False)
            self.models.move_to_end(key)
            return self.models[key]

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

    def client(self):
        # Behind the bundled reverse proxy every request arrives from the proxy, so the
        # sign-in limit uses the address the proxy appended last. Only trusted when enabled.
        forwarded = self.headers.get('X-Forwarded-For','') if os.getenv('COCKPIT_BEHIND_PROXY')=='1' else ''
        return forwarded.split(',')[-1].strip()[:64] or self.client_address[0]

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
        self.respond(status,ui.layout(self.lang,key,body,self.identity,self.csrf,self.snapshot,
                                      getattr(self,'demo_switch',False),getattr(self,'view_path','')),headers=headers)

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
        assets = {'app.css':'text/css; charset=utf-8','bern.jpg':'image/jpeg',
                  'bern-flag.png':'image/png','stadt-bern-logo.png':'image/png',
                  'stadt-bern-shield.png':'image/png','sem-shield.svg':'image/svg+xml'}
        if not post and path.startswith('/static/') and path[8:] in assets:
            asset = ROOT / path.lstrip('/')
            if asset.is_file():
                return self.respond(200,asset.read_bytes(),assets[path[8:]])
            return self.respond(404)
        if not post and path.startswith('/language/') and path.split('/')[-1] in ui.LOCALES:
            try:
                values = parse_qs(url.query,max_num_fields=10)
            except ValueError:
                return self.respond(400)
            view = '/'+values.get('view',[''])[0].lstrip('/')
            if view=='/case':
                view='/queue'
            routes = {'/login','/overview','/queue','/reports','/ai','/forecast','/intake','/help','/privacy','/ai-analysis'}
            if view not in routes and not re.fullmatch(r'/case/[A-Za-z0-9._~%\-]{1,180}',view):
                view = '/'
            filters = {key:values[key][0][:64] for key in ('q','state','page','goal','factor','topic','intent','asof') if key in values}
            return self.redirect(view+('?' + urlencode(filters) if filters else ''),
                                 [('Set-Cookie',self.cookie('locale',path.split('/')[-1],31536000))])
        self.view_path = self.path if not post else path
        self.demo_switch = False
        db = data.connect(self.server.path,initialize=False)
        try:
            token = cookie_value('sid')
            if re.fullmatch(r'[A-Za-z0-9_-]{40,60}',token):
                self.identity = db.execute('SELECT a.username,a.role,a.assignment,s.csrf,s.selected FROM sessions s JOIN accounts a USING(username) WHERE token=? AND expires>?',
                                           (digest(token),int(time.time()))).fetchone()
            if not self.identity:
                if path=='/privacy' and not post:
                    return self.page('privacy',ui.privacy(self.lang))
                if path!='/login':
                    return self.redirect('/login')
                return self.signin(db,post,cookie_value('login_csrf'))
            auth = self.identity
            self.csrf = auth['csrf']
            role = auth['role']
            self.demo_switch = role=='judge'
            if self.demo_switch:
                if path=='/demo-role' and post:
                    fields,_ = self.form(8192)
                    if not compare_digest(fields.get('csrf','').encode(),self.csrf.encode()):
                        return self.respond(403)
                    selected_role = fields.get('role')
                    if selected_role not in ('judge','worker','manager','importer'):
                        return self.respond(400)
                    with db:
                        if selected_role=='judge':
                            db.execute('DELETE FROM demo_roles WHERE session=?',(digest(token),))
                        else:
                            db.execute('INSERT INTO demo_roles VALUES(?,?) ON CONFLICT(session) DO UPDATE SET role=excluded.role',
                                       (digest(token),selected_role))
                    return self.redirect('/reports' if selected_role=='importer' else '/overview')
                persona = db.execute('SELECT role FROM demo_roles WHERE session=?',(digest(token),)).fetchone()
                if persona:
                    role = persona['role']
                    auth = dict(auth)
                    auth.update(role=role,assignment=data.DEMO_WORKERS[0] if role=='worker' else '')
                    self.identity = auth
            if path in ('/','/login') and not post:
                return self.redirect('/reports' if role=='importer' else '/overview')
            if path in ('/help','/privacy') and not post:
                self.snapshot = data.snapshot_metadata(db,auth['selected'],self.server.hosted)
                return self.page(path[1:],ui.guide(self.lang,role) if path=='/help' else ui.privacy(self.lang))
            allowed = {
              'judge':{'overview','queue','case','reports','export','ai','ai-analysis','forecast','forecast-upload','forecast-reset','intake','intake-save','intake-demo','seed','seed-invalid','quality','snapshot','import','analysis-export','logout'},
              'worker':{'overview','queue','case','reports','export','ai','intake','intake-save','intake-demo','snapshot','analysis-export','logout'},
              'manager':{'overview','reports','export','ai','ai-analysis','forecast','forecast-upload','forecast-reset','snapshot','analysis-export','logout'},
              'importer':{'reports','intake','intake-save','intake-demo','ai','seed','seed-invalid','quality','snapshot','import','analysis-export','logout'},
            }
            route = path.split('/')[1]
            if route not in allowed[role] or (self.server.hosted and
                    (route in ('import','forecast-upload','forecast-reset') or (route=='intake' and post))):
                return self.page('no_access',ui.heading(self.lang,'no_access'),403)
            mutations = {'logout','seed','seed-invalid','snapshot','import','intake-save','forecast-upload','forecast-reset','intake-demo'}
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
                if route in ('import','seed','seed-invalid'):
                    return self.import_snapshot(db,route,token,fields,files)
            if route in ('reports','quality'):
                self.snapshot = data.snapshot_metadata(db,auth['selected'],self.server.hosted)
                diagnostic = db.execute('SELECT * FROM import_diagnostics WHERE session=?',(digest(token),)).fetchone()
                if route=='reports':
                    return self.show_reports(db,diagnostic,query.get('notice',''))
                return self.quality(db,diagnostic)
            self.snapshot = data.snapshot_metadata(db,auth['selected'],self.server.hosted)
            if not self.snapshot:
                return self.page(route,ui.heading(self.lang,'empty'),404)
            if route=='ai':
                topic = query.get('topic','a1')
                intent = query.get('intent','entry_cohort')
                asof = query.get('asof',insights.RULE_DATES[0])
                if (set(query)-{'topic','intent','asof'} or intent not in insights.AGGREGATE_INTENTS
                    or topic not in insights.SOURCES or asof not in insights.RULE_DATES):
                    self.view_path = '/ai'
                    return self.page('ai',ui.heading(self.lang,'privacy_denied'),400)
                answer = insights.gateway(insights.RuleQuestion(topic,self.lang,asof))
                aggregate = None
                if role in ('judge','manager') and self.snapshot['source']=='synthetic':
                    trend = self.monthly_trend(db,'manager','') if intent=='monthly_change' else ()
                    cases = ()
                    if intent!='monthly_change':
                        _,cases = self.server.read_model(db,self.snapshot)
                    aggregate = insights.gateway(insights.AggregateQuestion(intent),self.snapshot['asof'],cases,trend)
                return self.page(route,ui.assistant(self.lang,topic,answer,aggregate,intent,asof))
            if role=='importer':
                _,tables = data.get_snapshot(db,self.snapshot['id'])
                cases = []
            else:
                tables,cases = self.server.read_model(db,self.snapshot)
            everyone = cases
            if role=='worker':
                cases = [c for c in cases if c['worker']==auth['assignment']]
            if route=='ai-analysis':
                return self.ai_analysis(db,everyone,query)
            if route in ('overview','analysis-export'):
                dimension = query.get('factor','year')
                if dimension not in rules.FACTOR_DIMENSIONS:
                    dimension = 'year'
                goal = int(query.get('goal','0'))
                if goal not in (0,1,2):
                    raise ValueError('invalid_metric')
                intake_categories = {}
                if dimension=='intake' and self.snapshot['source']=='synthetic':
                    if self.snapshot['asof']==data.PHASE5_MONTH:
                        intake_categories.update(data.phase5_categories(cases))
                    elif self.snapshot['asof'] in data.MONTHS:
                        intake_categories.update(data.story_intake(cases))
                    if self.server.hosted:
                        approved = db.execute('SELECT category FROM intake_demo WHERE session=? AND snapshot=?',
                                              (digest(token),self.snapshot['id'])).fetchone()
                        if approved:
                            intake_categories['DEMO-00001'] = approved['category']
                    else:
                        intake_categories.update(db.execute('SELECT person,category FROM intake WHERE snapshot=?',(self.snapshot['id'],)))
                if route=='analysis-export':
                    if self.snapshot['source']!='synthetic' or role=='importer':
                        return self.respond(403)
                    tabs = ui.analysis_export(self.lang,self.snapshot,cases,dimension,intake_categories,goal)
                    return self.respond(200,xlsx.write(tabs),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                        [('Content-Disposition','attachment; filename="safe-aggregates.xlsx"')])
                trend = self.monthly_trend(db,role,auth['assignment']) if self.snapshot['source']=='synthetic' else ()
                return self.page(route,ui.overview(self.lang,self.snapshot,cases,role=='manager',dimension,intake_categories,goal,trend,role in ('judge','manager')))
            if route=='queue':
                return self.page(route,ui.queue(self.lang,cases,query.get('q','')[:64],max(1,int(query.get('page','1'))),query.get('state',''),date.fromisoformat(self.snapshot['asof'])))
            if route=='case':
                identifier = unquote(path.split('/')[-1])
                case = next((c for c in cases if c['id']==identifier),None)
                if not case:
                    return self.page('case',ui.heading(self.lang,'empty'),404)
                model = predict.model_for(self.snapshot['id'],everyone,self.snapshot['asof'])
                contact = ui.demo_contact(case) if self.snapshot['source']=='synthetic' else None
                return self.page('case',ui.detail(self.lang,case,date.fromisoformat(self.snapshot['asof']),model.explain(case),contact))
            if route=='export':
                blob = xlsx.write(ui.export(self.lang,self.snapshot,cases,role))
                return self.respond(200,blob,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                    [('Content-Disposition','attachment; filename="cockpit.xlsx"')])
            if route=='forecast':
                stored = db.execute('SELECT series FROM forecast_input WHERE username=?',(auth['username'],)).fetchone() if not self.server.hosted else None
                series = json.loads(stored[0]) if stored else None
                report = insights.backtest([r[1] for r in series] if series else None)
                candidate = rules.evaluate(self.snapshot,tables,candidate=True) if self.snapshot['source']=='synthetic' else None
                rates = [min(100000,max(0,int(query.get('rate_'+key,'0')))) for key in ('a1','work','household')]
                return self.page(route,ui.forecast(self.lang,report,rates,cases,series,not self.server.hosted,
                                                   self.csrf,candidate,role=='judge'))
            if route in ('intake','intake-save','intake-demo'):
                return self.intake(db,route,post,fields if post else {},files if post else [],tables,cases,digest(token))
            return self.respond(404)
        except (ValueError, OverflowError, BadZipFile, ParseError, KeyError, IndexError):
            if path=='/ai':
                self.view_path = '/ai'
            return self.page('review',ui.heading(self.lang,'review'),400)
        finally:
            db.close()

    def ai_analysis(self,db,cases,query):
        asof = date.fromisoformat(self.snapshot['asof'])
        key = (self.snapshot['id'],self.lang)
        if query.get('refresh') or key not in self.server.ai_answers:
            model = predict.model_for(self.snapshot['id'],cases,self.snapshot['asof'])
            material = ui.analysis_material(cases,asof,model)
            instruction = ('Write five short observations and three concrete recommendations for the management of the asylum '
                           'social service, based only on these aggregate figures. Use plain sentences, one per line, no markdown.')
            answer,report = ai.ask(self.lang,instruction,material)
            with db:
                db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('ai_analysis',report['state']))
            self.server.ai_answers[key] = (answer,report)
        answer,report = self.server.ai_answers[key]
        return self.page('ai-analysis',ui.ai_analysis_page(self.lang,answer,report,ui.local_analysis(self.lang,cases,asof)))

    def monthly_trend(self,db,role,assignment):
        rows = db.execute('SELECT MAX(id) AS id FROM snapshots WHERE source="synthetic" AND asof IN (?,?) '
                          'GROUP BY asof ORDER BY asof',data.MONTHS).fetchall()
        trend = []
        for row in rows:
            snapshot = data.snapshot_metadata(db,row['id'],synthetic_only=True)
            if snapshot is None:
                continue
            _,cases = self.server.read_model(db,snapshot)
            if role=='worker':
                cases = [c for c in cases if c['worker']==assignment]
            metrics = rules.a1_totals(cases)
            eligible,on_time = metrics[1],metrics[8]
            if role=='manager' and min(on_time,eligible-on_time)<rules.MIN_GROUP:
                eligible = on_time = None
            trend.append((snapshot['asof'],eligible,on_time))
        return trend


    def signin(self,db,post,csrf):
        if not post:
            if not re.fullmatch(r'[A-Za-z0-9_-]{43}',csrf):
                csrf = secrets.token_urlsafe(32)
            return self.page('login',ui.login(self.lang,csrf),headers=[('Set-Cookie',self.cookie('login_csrf',csrf,600))])
        fields,_ = self.form(8192)
        valid_csrf = bool(csrf) and compare_digest(csrf.encode(),fields.get('csrf','').encode())
        if valid_csrf and self.server.allow_login(self.client()):
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

    def show_reports(self,db,diagnostic=None,notice='',status=200):
        history = db.execute('SELECT id,asof,source FROM snapshots WHERE (?=0 OR source="synthetic") ORDER BY asof DESC,id DESC',
                             (self.server.hosted,)).fetchall()
        issues = json.loads(diagnostic['issues']) if diagnostic else []
        records = self.manifest(db) if self.identity['role'] in ('judge','importer') else []
        if diagnostic and diagnostic['outcome']=='rejected':
            notice = 'rejected'
        return self.page('reports',ui.reports(self.lang,self.snapshot,history,self.identity['role'],self.csrf,self.server.hosted,
                                              notice,issues,records),status)

    def manifest(self,db):
        if not self.snapshot:
            return []
        return db.execute('SELECT dataset,sha256 FROM source_manifest WHERE snapshot=? ORDER BY dataset',
                          (self.snapshot['id'],)).fetchall()

    def quality(self,db,diagnostic):
        issues = json.loads(diagnostic['issues']) if diagnostic else []
        counts = json.loads(self.snapshot['inspected']) if self.snapshot else {}
        tabs = ui.quality_export(self.lang,self.snapshot,diagnostic,issues,counts,self.manifest(db))
        return self.respond(200,xlsx.write(tabs),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            [('Content-Disposition','attachment; filename="import-quality.xlsx"')])

    def import_snapshot(self,db,route,token,fields,files):
        report = fields.get('date','')
        if route in ('seed','seed-invalid'):
            if report not in (*data.MONTHS,data.PHASE4_MONTH,data.PHASE5_MONTH):
                raise ValueError('invalid_month')
            books = data.seed(report)
            if route=='seed-invalid':
                del books['language']
            inputs = books.values()
        else:
            inputs = [blob for name,blob in files if name=='workbooks']
        status = 'accepted'
        issues = []
        valid_report = None
        try:
            valid_report = date.fromisoformat(report).isoformat()
            selected,repeated = data.load_files(db,inputs,valid_report,'synthetic' if route!='import' else 'local')
            status = 'repeated' if repeated else 'accepted'
        except data.ImportFailure as exc:
            status,issues = 'rejected',exc.errors
        except ValueError:
            status,issues = 'rejected',[('snapshot',0,'invalid_date')]
        with db:
            db.execute('INSERT INTO import_diagnostics VALUES(?,?,?,?) ON CONFLICT(session) DO UPDATE SET '
                       'report_date=excluded.report_date,outcome=excluded.outcome,issues=excluded.issues',
                       (digest(token),valid_report,status,json.dumps(issues)))
            if status=='rejected':
                db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('snapshot_import','rejected'))
        if status=='rejected':
            self.snapshot = data.snapshot_metadata(db,self.identity['selected'],self.server.hosted)
            diagnostic = db.execute('SELECT * FROM import_diagnostics WHERE session=?',(digest(token),)).fetchone()
            return self.show_reports(db,diagnostic,'rejected',422)
        self.select(db,token,selected)
        return self.redirect('/reports?notice='+('repeated' if status=='repeated' else 'uploaded'))

    def intake(self,db,route,post,fields,files,tables,cases,session):
        lang = self.lang
        esc = ui.esc
        text = ui.text
        role = self.identity['role']
        authorized = {c['id'] for c in cases}
        if role=='importer':
            authorized = {r['_person'] for r in tables['clients']}
        num_to_person = {r['Zemis Nummer']:r['_person'] for r in tables['clients'] if r['_person'] in authorized}
        if route=='intake-save':
            pid = fields.get('person') or num_to_person.get(fields.get('zemis','').strip())
            category = fields.get('category')
            if pid not in authorized or category not in insights.CATEGORIES:
                raise ValueError('invalid_approval')
            with db:
                if self.server.hosted:
                    if pid!='DEMO-00001' or self.snapshot['source']!='synthetic':
                        return self.respond(403)
                    db.execute('INSERT INTO intake_demo VALUES(?,?,?) ON CONFLICT(session,snapshot) DO UPDATE SET category=excluded.category',
                               (session,self.snapshot['id'],category))
                else:
                    db.execute('INSERT INTO intake VALUES(?,?,?) ON CONFLICT(snapshot,person) DO UPDATE SET category=excluded.category',
                               (self.snapshot['id'],pid,category))
                db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('intake_review','accepted'))
            return self.redirect('/intake')
        feedback = ''
        if post:
            if route=='intake-demo' and not files:
                blob = Path(__file__).with_name('synthetic-intake.pdf').read_bytes()
            elif not self.server.hosted and len(files)==1 and files[0][0]=='report':
                blob = files[0][1]
            else:
                raise ValueError('expected_pdf')
            result = intake.suggest(blob,num_to_person)
            if result['mode']=='review':
                options = ''.join(f'<option value="{key}" {"selected" if key in result["suggestions"] else ""}>{text(lang,key)}</option>'
                                  for key in insights.CATEGORIES)
                extraction = f'<p>{text(lang,"ocr_review")}</p>' if result.get('extraction')=='ocr' else ''
                known = [r['Zemis Nummer'] for r in tables['clients']]+[r['_person'] for r in tables['clients']]
                answer,report = ai.ask(lang,'Summarise this masked intake form in three sentences and name the main obstacle to a '
                                       'language course (childcare scheduling, prior schooling, course participation or housing). '
                                       'No markdown.',result['text'],known)
                with db:
                    db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('intake_ai',report['state']))
                local = [text(lang,'reviewed_intake')+' · '+', '.join(text(lang,k) for k in result['suggestions'])] if result['suggestions'] else [text(lang,'manual')]
                extraction += ui.shield_panel(lang,report)+f'<section class="panel ai-panel">{ui.ai_answer(lang,answer,report,local)}</section>'
                feedback = extraction + ui.post('/intake-save',self.csrf,f'<p>{esc(result["person"])}</p>'
                    f'<input type="hidden" name="person" value="{esc(result["person"])}">'
                    f'<label>{text(lang,"category")} <select name="category">{options}</select></label>'+ui.action(lang,'review_save')+ui.tip(lang,'help_review_save'))
            else:
                feedback = f'<p role="status">{text(lang,"manual")}</p>'
        sample = ui.post('/intake-demo',self.csrf,ui.action(lang,'intake_sample')+ui.tip(lang,'help_pdf_sample'))
        if self.server.hosted:
            saved = db.execute('SELECT category FROM intake_demo WHERE session=? AND snapshot=?',
                               (session,self.snapshot['id'])).fetchone()
            approval = f'<p>{text(lang,"reviewed_intake")} · {text(lang,saved["category"])}</p>' if saved else ''
            return self.page('intake',ui.heading(lang,'intake')+
                             f'<section class="panel"><p>{text(lang,"synthetic_only")}</p>{sample}{feedback}{approval}</section>')
        saved = list(db.execute('SELECT person,category FROM intake WHERE snapshot=?',(self.snapshot['id'],)))
        if role=='importer':
            approvals = f'<p>{text(lang,"rows")} {len(saved)}</p>'
        else:
            approvals = ui.table(['ID',ui.tr(lang,'category')],((esc(r['person']),text(lang,r['category'])) for r in saved if r['person'] in authorized))
        form = ui.post('/intake',self.csrf,'<label>PDF <input type="file" name="report" accept=".pdf" required></label>'+ui.action(lang,'pdf_review')+ui.tip(lang,'help_pdf'),True)
        manual_options = ''.join(f'<option value="{k}">{text(lang,k)}</option>' for k in insights.CATEGORIES)
        manual = ui.post('/intake-save',self.csrf,
            f'<label>ZEMIS <input name="zemis" required></label><label>{text(lang,"category")} '
            f'<select name="category">{manual_options}</select></label>'+ui.action(lang,'review_save')+ui.tip(lang,'help_manual'))
        return self.page('intake',ui.heading(lang,'intake')+
                         f'<section class="panel">{form}{sample}{feedback}{approvals}<details><summary>{text(lang,"manual")}</summary>{manual}</details></section>')


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
    commands.add_parser('revoke-sessions')
    snapshot_backup = commands.add_parser('backup')
    snapshot_backup.add_argument('destination', type=Path)
    seeds = commands.add_parser('fixtures')
    seeds.add_argument('--output',default='runtime/fixtures')
    seeds.add_argument('--people',type=int,default=None)
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
    if args.command in ('backup','revoke-sessions') and not path.is_file():
        parser.error('The source database does not exist')
    path.parent.mkdir(exist_ok=True,parents=True)
    db = data.connect(path)
    if args.command=='backup':
        data.backup(db,args.destination)
        print('Verified SQLite backup created')
    elif args.command=='revoke-sessions':
        print(f'Sessions revoked: {data.revoke_sessions(db)}')
    elif args.command=='account':
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
            with App((args.bind,args.port),path,args.hosted) as server:
                print(f'Listening on {args.bind}:{server.server_port}',flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
            return
    db.close()


if __name__=='__main__':
    main()
