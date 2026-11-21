"""Source contracts, deterministic fixtures and transactional snapshot storage."""
from collections import defaultdict
from contextlib import closing
from datetime import date, timedelta, datetime, timezone
from hashlib import sha256
from pathlib import Path
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError
import json
import sqlite3
import unicodedata

from . import xlsx

SCHEMA = json.loads(Path(__file__).with_name('schema.json').read_text())
DATES = {
    'clients': ('Zuständigkeitsbeginn','Zuständigkeitsende','Datum Übergang Gemeindezuständigkeit','Geburtsdatum'),
    'events': ('Ereignisdatum','Erledigungsdatum'),
    'status': ('Verfahrensstand Gültig ab','Verfahrensstand Gültig bis'),
    'membership': ('Dossierperson Von','Dossierperson Bis'),
    'work': ('Von','Bis'), 'support': ('Finanzielle Unterstützung Gültig von','Finanzielle Unterstützung Gültig bis'),
    'education': ('Start','Abschluss'), 'official': ('Erreicht am',), 'language': ('Datum Erreichung',),
    'housing': ('Unterbringung Von','Unterbringung Bis'), 'zemis': ('Arbeitsbeginn','Verpflichtet bis'),
}
IDS = ('Klientennummer','Zemis Nummer','Klient/-in Zemis-Nr.','Dossier-Nr.')
PAIR = {'status': DATES['status'], 'membership': DATES['membership'], 'work': DATES['work'], 'support': DATES['support'],
        'education': DATES['education'], 'housing': DATES['housing'], 'zemis': DATES['zemis'],
        'clients': DATES['clients'][:2]}
MONTHS = ('2026-09-30','2026-10-31')
PHASE4_MONTH = '2026-08-31'
PHASE5_MONTH = '2026-07-31'



def norm(value):
    return ' '.join(unicodedata.normalize('NFC',value).split()) if isinstance(value,str) else value


def seed(asof, size=144):
    rows = defaultdict(list)
    phase4 = asof==PHASE4_MONTH
    phase5 = asof==PHASE5_MONTH
    if phase5:
        size = max(480,size)
    def add(key, values):
        rows[key].append([values.get(header) for header in SCHEMA[key]['headers']])
    for i in range(size):
        person = f'DEMO-{i+1:05}'
        z = f'SYN-Z{i+1:05}'
        household = f'SYN-H{i//2+1:05}'
        ids = {'Klientennummer':person,'Zemis Nummer':z,'Klient/-in Zemis-Nr.':z,'Dossier-Nr.':household}
        entry = date(2022+i%4, 10 if i == 1 else 1+i%12, 1+i%24)
        if phase5:
            entry = date(2022+(i//6)%2,1+i%6,1+i%24)
        elif i == 0:
            entry = date(2023,10,16)
        status = ('VA','B-FL','F-FL','B-RSFL','S','N (Asylsuchende)')[i%6]
        end = date(2028+(i//2)%2,6,30)
        worker = ('A','B','C')[(i//2)%3]
        add('clients', ids | {'Geburtsdatum':date(1977+i%36,4,8),'Zuständigkeitsbeginn':entry,'Zuständigkeitsende':end,
                             'Datum Übergang Gemeindezuständigkeit':None,'Fallführung':worker,'Verfahrensstand':status,
                             'Schuljahre vor Einreise':4+i%12,'Muttersprache':('Arabisch','Tigrinya','Dari')[i%3]})
        add('events',ids | {'Asylgeschäftsart':'Aufenthalt (Einreise)','Ereignisdatum':entry})
        add('events',ids | {'Asylgeschäftsart':'Asylgesuch in CH (Kt normal, Kat. III)','Ereignisdatum':entry + timedelta(days=2)})
        add('status',ids | {'Verfahrensstand Gültig ab':entry,'Verfahrensstand':status})
        member_start = date(2026,6,1) if phase4 and i==1 else entry
        add('membership',ids | {'Dossierperson Von':member_start,'Rolle':'Familienmitglied'})
        add('housing',ids | {'Unterbringung Von':entry,'Unterbringung Art':'Wohnung','PLZ':'3000','Ort':'Bern'})
        if i%4 != 3:
            proof = entry+timedelta(days=(150 if (i//6)%10<5 else 1250)) if phase5 else (date(2026,10,12) if i == 0 else entry + timedelta(days=200+i*11))
            if str(proof) <= asof:
                add('language', ids | {'Sprache':'Deutsch','Sprachniveau':'A2' if i%5 else 'A1',
                     'Art':'Zertifizierung','Bemerkungen':'fide','Datum Erreichung':proof})
                if i%7:
                    add('official',ids | {'Art':'Sprachniveau A1','Erreicht am':proof,'Jahr Grundgesamtheit':entry.year,'Ziel mit Status S erreicht':'Nein'})
        if phase4 and i==1:
            for begin, finish in ((date(2026,1,1),date(2026,3,31)),(date(2026,4,2),None)):
                add('work',ids | {'Von':begin,'Bis':finish,'Pensum %':80,'Erwerbsstatus':'unselbstständig',
                                  'Bemerkungen':'Demo: 1. Arbeitsmarkt'})
        elif i%3:
            job = max(entry,date(2025,3+i%8,1))
            add('work',ids | {'Von':job,'Pensum %':80 if i%5 else 50,'Arbeitgeber Name':'Demo Betrieb','Erwerbsstatus':'unselbstständig','Bemerkungen':'Demo: 1. Arbeitsmarkt'})
        if i%3 or i%11 == 0:
            add('zemis',ids | {'Arbeitsbeginn':max(entry,date(2025,3+i%8,1)),'Betrieb':'Demo Betrieb'})
        if i%3 == 0:
            add('education',ids | {'Start':max(entry,date(2025,8,1)),'Art':'Sek II' if i%4==0 else 'Förderangebot Sprache',
                                   'Institution Name':'Demo Lernzentrum','Stunden pro Woche':8})
        if i%2 == 0:
            add('support',ids | {'Unterstützung':None if phase4 and i==2 else 'Sozialhilfe','Finanzielle Unterstützung Gültig von':date(2022,1,1),
                'Finanzielle Unterstützung Gültig bis':date(2025,8,15) if i%4==0 else None})
    return {key:xlsx.write({key:[spec['headers'],*rows[key]]}) for key,spec in SCHEMA.items()}


def phase5_categories(cases):
    """Fictional pre-reviewed records for the dedicated synthetic analysis fixture."""
    categories = ('schooling','course','scheduling','housing')
    sample = ((case['id'],int(case['id'].removeprefix('DEMO-'))-1) for case in cases)
    return {identifier:categories[(n//13)%len(categories)] for identifier,n in sample if n%7}


class ImportFailure(Exception):
    def __init__(self, errors):
        self.errors = errors


def connect(path):
    db = sqlite3.connect(path,timeout=30)
    db.row_factory = sqlite3.Row
    db.executescript("""
      PRAGMA foreign_keys=ON;
      CREATE TABLE IF NOT EXISTS snapshots(
        id INTEGER PRIMARY KEY, asof TEXT NOT NULL, source TEXT NOT NULL, digest TEXT UNIQUE,
        created TEXT NOT NULL, inspected TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS source_rows(
        snapshot INTEGER REFERENCES snapshots(id) ON DELETE CASCADE,
        dataset TEXT, line INTEGER, content TEXT, PRIMARY KEY(snapshot,dataset,line));
      CREATE TABLE IF NOT EXISTS accounts(username TEXT PRIMARY KEY, password TEXT, role TEXT, assignment TEXT);
      CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, username TEXT REFERENCES accounts(username),
        csrf TEXT, expires INTEGER, selected INTEGER REFERENCES snapshots(id) ON DELETE SET NULL);
      CREATE TABLE IF NOT EXISTS source_manifest(
        snapshot INTEGER REFERENCES snapshots(id) ON DELETE CASCADE,
        dataset TEXT, sha256 TEXT NOT NULL, PRIMARY KEY(snapshot,dataset));
      CREATE TABLE IF NOT EXISTS import_diagnostics(
        session TEXT PRIMARY KEY REFERENCES sessions(token) ON DELETE CASCADE,
        report_date TEXT, outcome TEXT NOT NULL, issues TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS audit(at TEXT, action TEXT, outcome TEXT);
      CREATE TABLE IF NOT EXISTS forecast_input(
        username TEXT PRIMARY KEY REFERENCES accounts(username) ON DELETE CASCADE, series TEXT);
      CREATE TABLE IF NOT EXISTS demo_roles(
        session TEXT PRIMARY KEY REFERENCES sessions(token) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK(role IN ('worker','manager','importer')));
      CREATE TABLE IF NOT EXISTS intake_demo(
        session TEXT REFERENCES sessions(token) ON DELETE CASCADE,
        snapshot INTEGER REFERENCES snapshots(id) ON DELETE CASCADE,
        category TEXT NOT NULL, PRIMARY KEY(session,snapshot));
      CREATE TABLE IF NOT EXISTS intake(snapshot INTEGER REFERENCES snapshots(id) ON DELETE CASCADE,
        person TEXT, category TEXT, PRIMARY KEY(snapshot,person));
    """)
    return db


def load_files(db, files, asof, source):
    report = date.fromisoformat(asof)
    recognized = {}
    issues = []
    hashed = sha256(f'{report}:{source}'.encode())
    headers = {frozenset(item['headers']):key for key,item in SCHEMA.items()}
    for n, blob in enumerate(files,1):
        try:
            stream = xlsx.read(blob)
            _, header, mac = next(stream)
            header = tuple(norm(value) for value in header)
            key = headers.get(frozenset(header)) if len(set(header)) == len(header) else None
            if key is None or key in recognized:
                raise ValueError('unknown_or_duplicate_contract')
            recognized[key] = (blob, header, mac)
        except (ValueError,TypeError,OverflowError,BadZipFile,KeyError,StopIteration,ParseError,IndexError):
            issues.append((f'file {n}',1,'unrecognized_or_invalid_workbook'))
        finally:
            stream.close()
    issues.extend((key,1,'missing_source') for key in SCHEMA.keys()-recognized.keys())
    if issues:
        raise ImportFailure(issues)
    for key,(blob,_,_) in sorted(recognized.items()):
        hashed.update(key.encode())
        hashed.update(sha256(blob).digest())
    digest = hashed.hexdigest()
    count = {}
    clients, zemis, homes = {}, {}, set()
    current_status = defaultdict(set)
    with db:
        cursor = db.execute('INSERT OR IGNORE INTO snapshots(asof,source,digest,created,inspected) VALUES(?,?,?,?,?)',
                            (asof,source,digest,datetime.now(timezone.utc).isoformat(),'{}'))
        if cursor.rowcount == 0:
            snapshot = db.execute('SELECT id FROM snapshots WHERE digest=?',(digest,)).fetchone()[0]
        else:
            snapshot = cursor.lastrowid
        db.executemany('INSERT OR IGNORE INTO source_manifest VALUES(?,?,?)',
                       ((snapshot,key,sha256(blob).hexdigest()) for key,(blob,_,_) in recognized.items()))
        if cursor.rowcount == 0:
            return snapshot, True
        for key in ['clients',*(k for k in SCHEMA if k!='clients')]:
            blob, header, mac = recognized[key]
            seen = set()
            batch = []
            count[key] = 0
            for line, cells, _ in read_data_rows(blob,key):
                if len(issues) >= 100:
                    break
                if not any(x not in (None,'') for x in cells):
                    continue
                if any(value not in (None,'') for value in cells[len(header):]):
                    issues.append((key,line,'unexpected_column'))
                    continue
                row = dict(zip(header,(norm(value) for value in cells),strict=False))
                try:
                    if any(row.get(k) is not None and not isinstance(row[k],str) for k in IDS):
                        raise ValueError('numeric_identifier')
                    for k in DATES[key]:
                        value = xlsx.excel_date(row.get(k),mac)
                        row[k] = value.isoformat() if value else None
                    if key in PAIR:
                        start,end = (row.get(k) for k in PAIR[key])
                        if start and end and start>end:
                            raise ValueError('date_range')
                    canonical = json.dumps(row,ensure_ascii=False,sort_keys=True)
                    if canonical in seen:
                        raise ValueError('duplicate_row')
                    seen.add(canonical)
                    person = row.get('Klientennummer')
                    zid = row.get('Zemis Nummer') or row.get('Klient/-in Zemis-Nr.')
                    home = row.get('Dossier-Nr.')
                    if key == 'clients':
                        if not person or not zid or not home or person in clients or zid in zemis:
                            raise ValueError('invalid_or_conflicting_client_key')
                        clients[person] = zid
                        zemis[zid] = person
                        homes.add(home)
                    else:
                        if key in ('support','membership') and home not in homes:
                            raise ValueError('unresolved_household')
                        if key != 'support' and ((not person and not zid) or (person and person not in clients)
                             or (zid and zid not in zemis) or (person and zid and clients[person] != zid)):
                            raise ValueError('unresolved_or_conflicting_person')
                        if key=='status' and start and start<=asof and (not end or end>=asof):
                            identity = person or zemis[zid]
                            current_status[identity].add(row.get('Verfahrensstand'))
                            if len(current_status[identity])>1:
                                raise ValueError('conflicting_current_status')
                    row['_person'] = person or zemis.get(zid)
                    row['_line'] = line
                    batch.append((snapshot,key,line,json.dumps(row,ensure_ascii=False)))
                    count[key]+=1
                    if len(batch)==500:
                        db.executemany('INSERT INTO source_rows VALUES(?,?,?,?)',batch)
                        batch.clear()
                except (ValueError,TypeError,OverflowError) as exc:
                    code = str(exc)
                    issues.append((key,line,code if code.replace('_','').isalpha() and ' ' not in code else 'invalid_value'))
            db.executemany('INSERT INTO source_rows VALUES(?,?,?,?)',batch)
        if not clients:
            issues.append(('clients',1,'empty_clients'))
        if issues:
            raise ImportFailure(issues)
        db.execute('UPDATE snapshots SET inspected=? WHERE id=?',(json.dumps(count),snapshot))
        db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('snapshot_import','accepted'))
    return snapshot, False



def read_data_rows(blob,key):
    line = 1
    try:
        with closing(xlsx.read(blob)) as stream:
            next(stream)
            for line, cells, mac in stream:
                yield line, cells, mac
    except (ValueError,TypeError,OverflowError,BadZipFile,KeyError,StopIteration,ParseError,IndexError) as exc:
        raise ImportFailure([(key,line+1,'invalid_worksheet_data')]) from exc


def snapshot_metadata(db, id=None, synthetic_only=False):
    return db.execute(
        'SELECT * FROM snapshots WHERE (? IS NULL OR id=?) AND (?=0 OR source="synthetic") '
        'ORDER BY asof DESC,id DESC LIMIT 1',(id,id,synthetic_only)).fetchone()



def get_snapshot(db, id=None):
    row = snapshot_metadata(db,id)
    if not row:
        return None, {}
    data = defaultdict(list)
    for entry in db.execute('SELECT dataset,content FROM source_rows WHERE snapshot=? ORDER BY dataset,line',(row['id'],)):
        data[entry['dataset']].append(json.loads(entry['content']))
    return row,data


def backup(db, destination):
    """Create a consistent private backup without replacing an existing file."""
    import os
    from tempfile import mkstemp
    destination = Path(destination)
    parent = destination.parent
    fd, temporary = mkstemp(prefix='.cockpit-backup-',dir=parent)
    os.close(fd)
    try:
        with closing(sqlite3.connect(temporary)) as copy:
            db.backup(copy)
            if copy.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise OSError('backup integrity check failed')
        os.link(temporary,destination)
    finally:
        os.unlink(temporary)
