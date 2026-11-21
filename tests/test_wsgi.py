from io import BytesIO
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import urlencode
import importlib
import os
import re


class ServerlessTests(TestCase):
    """The WSGI entry serves the hosted profile and keeps sessions valid across fresh instances."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.env = patch.dict(os.environ,{'COCKPIT_DB':self.tmp.name+'/a.sqlite','COCKPIT_DEMO_USER':'jury',
                                          'COCKPIT_DEMO_PASSWORD':'correct-horse-battery','COCKPIT_SESSION_SECRET':'s'*40})
        self.env.start()
        from cockpit import wsgi
        self.wsgi = importlib.reload(wsgi)
        self.cookies = {}

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def call(self, method, path, form=None):
        body = urlencode(form).encode() if form else b''
        path,_,query = path.partition('?')
        environ = {'REQUEST_METHOD':method,'PATH_INFO':path,'QUERY_STRING':query,'wsgi.input':BytesIO(body),
                   'CONTENT_LENGTH':str(len(body)),'REMOTE_ADDR':'10.0.0.1','HTTP_X_FORWARDED_FOR':'198.51.100.4',
                   'HTTP_COOKIE':'; '.join(f'{k}={v}' for k,v in self.cookies.items())}
        if form:
            environ['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        seen = {}
        def start(status, headers):
            seen['status'],seen['headers'] = int(status.split()[0]),headers
        payload = b''.join(self.wsgi.app(environ,start))
        for key,value in seen['headers']:
            if key.lower()=='set-cookie':
                name,val = value.split(';')[0].split('=',1)
                self.cookies[name] = val
        return seen['status'],payload

    def test_sign_in_survives_a_new_instance(self):
        _,page = self.call('GET','/login')
        token = re.search(rb'name="csrf" value="([^"]+)"',page)[1].decode()
        self.assertEqual(self.call('POST','/login',{'csrf':token,'username':'jury','password':'correct-horse-battery'})[0],303)
        self.assertEqual(self.call('GET','/overview')[0],200)
        # A cold start on another instance: new database file, same secret.
        os.environ['COCKPIT_DB'] = self.tmp.name+'/b.sqlite'
        self.wsgi = importlib.reload(self.wsgi)
        status,page = self.call('GET','/case/DEMO-00006')
        self.assertEqual(status,200)
        self.assertIn(b'pred-figure',page)
        self.assertEqual(self.call('GET','/static/app.css')[0],200)
        self.assertEqual(self.call('POST','/import',{'csrf':'x'})[0],403)

    def test_forged_session_is_refused(self):
        self.cookies['sid'] = 'eyJmb28iOiJiYXIifQ.'+'A'*43
        self.assertEqual(self.call('GET','/overview')[0],303)

    def test_missing_configuration_is_reported(self):
        os.environ['COCKPIT_DEMO_PASSWORD'] = ''
        self.wsgi = importlib.reload(self.wsgi)
        self.assertEqual(self.call('GET','/login')[0],503)
