"""WSGI entry for serverless hosts (Vercel). Runs the hosted, synthetic-only profile.

Each instance builds its own demo database in /tmp on first request. Sessions are signed with
COCKPIT_SESSION_SECRET so they stay valid when a later request lands on another instance.
Required environment: COCKPIT_DEMO_USER, COCKPIT_DEMO_PASSWORD, COCKPIT_SESSION_SECRET.
"""
from http.client import responses
from io import BytesIO
from pathlib import Path
from threading import Lock
import os

from . import data
from .server import App, Handler, account

os.environ.setdefault('COCKPIT_BEHIND_PROXY','1')
DB = Path(os.getenv('COCKPIT_DB','/tmp/cockpit.sqlite'))
_service = None
_lock = Lock()


class Connection:
    """In-memory socket stand-in: the handler reads the request and writes the response here."""

    def __init__(self, request):
        self.request, self.output = request, BytesIO()

    def makefile(self, mode, *_args, **_kwargs):
        return BytesIO(self.request) if 'r' in mode else self.output

    def sendall(self, payload):
        self.output.write(payload)

    def settimeout(self, _seconds):
        pass

    def close(self):
        pass


def service():
    global _service
    with _lock:
        if _service is None:
            user,password = os.getenv('COCKPIT_DEMO_USER',''),os.getenv('COCKPIT_DEMO_PASSWORD','')
            if not user or len(password)<12 or len(os.getenv('COCKPIT_SESSION_SECRET',''))<32:
                raise RuntimeError('Set COCKPIT_DEMO_USER, COCKPIT_DEMO_PASSWORD (12+ chars) and COCKPIT_SESSION_SECRET (32+ chars)')
            db = data.connect(DB)
            try:
                for month in data.MONTHS:
                    if not db.execute('SELECT 1 FROM snapshots WHERE source="synthetic" AND asof=?',(month,)).fetchone():
                        data.load_files(db,data.seed(month).values(),month,'synthetic')
                if not db.execute('SELECT 1 FROM accounts WHERE username=?',(user,)).fetchone():
                    account(db,user,password,'judge')
            finally:
                db.close()
            state = App.__new__(App)
            state.setup_state(DB,True)
            _service = state
        return _service


def app(environ, start_response):
    try:
        server = service()
    except RuntimeError as error:
        start_response('503 Service Unavailable',[('Content-Type','text/plain; charset=utf-8')])
        return [str(error).encode()]
    path = environ.get('RAW_URI') or (environ.get('PATH_INFO','/')+('?'+environ['QUERY_STRING'] if environ.get('QUERY_STRING') else ''))
    length = int(environ.get('CONTENT_LENGTH') or 0)
    body = environ['wsgi.input'].read(length) if length else b''
    headers = [(key[5:].replace('_','-').title(),value) for key,value in environ.items() if key.startswith('HTTP_')]
    if environ.get('CONTENT_TYPE'):
        headers.append(('Content-Type',environ['CONTENT_TYPE']))
    if body:
        headers.append(('Content-Length',str(len(body))))
    request = f'{environ["REQUEST_METHOD"]} {path} HTTP/1.0\r\n'.encode('latin-1')
    request += b''.join(f'{k}: {v}\r\n'.encode('latin-1') for k,v in headers)+b'\r\n'+body
    connection = Connection(request)
    Handler(connection,(environ.get('REMOTE_ADDR','0.0.0.0'),0),server)
    raw = connection.output.getvalue()
    head,_,payload = raw.partition(b'\r\n\r\n')
    status_line,*lines = head.decode('latin-1').split('\r\n')
    code = int(status_line.split()[1])
    response_headers = [tuple(part.strip() for part in line.split(':',1)) for line in lines
                        if ':' in line and line.split(':',1)[0].lower() not in ('server','date','connection')]
    start_response(f'{code} {responses.get(code,"")}',response_headers)
    return [payload]
