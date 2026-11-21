from http.client import HTTPConnection
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest import TestCase
from urllib.parse import urlencode
from io import BytesIO
from zipfile import ZipFile
import os
import re
import secrets

from cockpit import data
from cockpit.server import App, account


class HTTPTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = TemporaryDirectory()
        cls.path = Path(cls.tmp.name)/'test.sqlite'
        db=data.connect(cls.path)
        cls.first,cls.second = [data.load_files(db,data.seed(d).values(),d,'synthetic')[0] for d in data.MONTHS]
        cls.password=secrets.token_urlsafe(20)
        for name,role,assignment in [('judging','judge',''),('worker','worker',data.DEMO_WORKERS[1]),('manager','manager','')]:
            account(db,name,cls.password,role,assignment)
        db.close()
        cls.server=App(('127.0.0.1',0),cls.path,False)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def request(self,path,form=None):
        connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
        headers={'Cookie':'; '.join(f'{k}={v}' for k,v in self.cookies.items())}
        if form is not None:
            headers['Content-Type']='application/x-www-form-urlencoded'
        connection.request('GET' if form is None else 'POST',path,urlencode(form) if form is not None else None,headers)
        response=connection.getresponse()
        for key,value in response.getheaders():
            if key.lower()=='set-cookie':
                k,v=value.split(';')[0].split('=',1)
                self.cookies[k]=v
        result=response.status,response.read()
        connection.close()
        return result

    def setUp(self):
        self.cookies={}
        self.server.attempts.clear()

    def login(self,user):
        status,body=self.request('/login')
        self.assertEqual(status,200)
        token=re.search(rb'name="csrf" value="([^"]+)"',body)[1].decode()
        self.assertEqual(self.request('/login',{'csrf':token,'username':user,'password':self.password})[0],303)
        status,body=self.request('/reports')
        self.assertEqual(status,200)
        return re.search(rb'name="csrf" value="([^"]+)"',body)[1].decode()

    def test_sign_in_limit_is_per_forwarded_client_behind_proxy(self):
        def attempt(forwarded):
            connection = HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
            connection.request('GET','/login',headers={'X-Forwarded-For':forwarded})
            response = connection.getresponse()
            cookie = [v for k,v in response.getheaders() if k.lower()=='set-cookie'][0].split(';')[0]
            token = re.search(rb'name="csrf" value="([^"]+)"',response.read())[1].decode()
            connection.close()
            connection = HTTPConnection('127.0.0.1',self.server.server_port,timeout=10)
            connection.request('POST','/login',urlencode({'csrf':token,'username':'judging','password':self.password}),
                               {'Content-Type':'application/x-www-form-urlencoded','Cookie':cookie,'X-Forwarded-For':forwarded})
            status = connection.getresponse().status
            connection.close()
            return status
        os.environ['COCKPIT_BEHIND_PROXY'] = '1'
        try:
            self.assertEqual({attempt(f'198.51.100.{i}') for i in range(12)},{303})
            self.assertEqual([attempt('203.0.113.9') for _ in range(9)][-1],401)
        finally:
            del os.environ['COCKPIT_BEHIND_PROXY']
            self.server.attempts.clear()

    def test_login_form_survives_favicon_and_parallel_login_tab(self):
        _, body = self.request('/login')
        csrf = re.search(rb'name="csrf" value="([^"]+)"',body)[1].decode()
        self.assertEqual(self.request('/favicon.ico')[0],204)
        self.assertEqual(self.request('/login')[0],200)
        self.assertEqual(self.cookies['login_csrf'],csrf)
        self.assertEqual(self.request('/login',{'csrf':csrf,'username':'judging','password':self.password})[0],303)

    def test_anonymous_role_isolation_and_logout(self):
        for path in ('/overview','/case/DEMO-00001','/export','/ai','/forecast','/intake'):
            self.assertEqual(self.request(path)[0],303)
        csrf=self.login('worker')
        self.assertEqual(self.request('/case/DEMO-00001')[0],404)
        self.assertEqual(self.request('/case/DEMO-00003')[0],200)
        self.assertEqual(self.request('/forecast')[0],403)
        status,book=self.request('/export')
        self.assertEqual(status,200)
        with ZipFile(BytesIO(book)) as z:
            self.assertFalse(any(b'DEMO-00001' in z.read(name) for name in z.namelist()))
        self.assertEqual(self.request('/logout',{'csrf':csrf})[0],303)
        self.assertEqual(self.request('/export')[0],303)

    def test_manager_and_invalid_csrf(self):
        self.login('manager')
        self.assertEqual(self.request('/case/DEMO-00001')[0],403)
        self.assertEqual(self.request('/queue')[0],403)
        self.assertEqual(self.request('/snapshot',{'csrf':'bad','id':self.first})[0],403)
        self.assertEqual(self.request('/ai?topic=CANARY-SECRET')[0],400)
        self.assertEqual(self.request('/forecast')[0],200)

    def test_quality_report_rejection_preserves_selected_month_and_is_session_scoped(self):
        self.assertEqual(self.request('/quality')[0],303)
        csrf = self.login('judging')
        september, october = data.MONTHS
        self.assertEqual(self.request('/seed',{'csrf':csrf,'date':september})[0],303)
        expected = self.request('/export')[1]
        status, html = self.request('/seed-invalid',{'csrf':csrf,'date':october})
        self.assertEqual(status,422)
        self.assertIn(b'language',html)
        self.assertIn(b'2026-09-30',html)
        self.assertEqual(self.request('/export')[1],expected)
        status, report = self.request('/quality')
        self.assertEqual(status,200)
        with ZipFile(BytesIO(report)) as archive:
            self.assertIn(b'missing_source',archive.read('xl/worksheets/sheet3.xml'))
            self.assertIn(b'<v>46295</v>',archive.read('xl/worksheets/sheet1.xml'))
            self.assertIn(b'<v>46326</v>',archive.read('xl/worksheets/sheet1.xml'))
            self.assertIn(b'SHA-256',archive.read('xl/worksheets/sheet2.xml'))
            self.assertFalse(any(b'DEMO-00001' in archive.read(name) for name in archive.namelist()))
        self.cookies.clear()
        self.login('manager')
        self.assertEqual(self.request('/quality')[0],403)
        self.cookies.clear()
        self.login('judging')
        with ZipFile(BytesIO(self.request('/quality')[1])) as archive:
            self.assertNotIn(b'missing_source',archive.read('xl/worksheets/sheet3.xml'))

    def test_hosted_pdf_sample_and_aggregate_export_are_scoped(self):
        self.server.hosted = True
        try:
            csrf = self.login('judging')
            self.assertEqual(self.request('/seed',{'csrf':csrf,'date':data.PHASE5_MONTH})[0],303)
            self.assertEqual(self.request('/intake',{'csrf':csrf})[0],403)
            status, proposal = self.request('/intake-demo',{'csrf':csrf})
            self.assertEqual(status,200)
            self.assertIn(b'DEMO-00001',proposal)
            self.assertIn(b'value="scheduling" selected',proposal)
            self.assertEqual(self.request('/intake-save',{'csrf':csrf,'person':'DEMO-00001','category':'scheduling'})[0],303)
            self.assertIn(b'Best',self.request('/intake')[1])
            status, workbook = self.request('/analysis-export?factor=year&goal=0')
            self.assertEqual(status,200)
            with ZipFile(BytesIO(workbook)) as archive:
                self.assertIn(b'160',archive.read('xl/worksheets/sheet2.xml'))
                self.assertNotIn(b'DEMO-00001',archive.read('xl/worksheets/sheet2.xml'))
            self.cookies.clear()
            self.login('judging')
            self.assertNotIn('Bestätigte Kategorie'.encode(),self.request('/intake')[1])
        finally:
            self.server.hosted = False

    def test_local_judge_can_switch_to_restricted_views(self):
        csrf = self.login('judging')
        self.assertEqual(self.request('/demo-role',{'csrf':csrf,'role':'worker'})[0],303)
        self.assertEqual(self.request('/case/DEMO-00003')[0],404)
        self.assertEqual(self.request('/demo-role',{'csrf':csrf,'role':'manager'})[0],303)
        self.assertEqual(self.request('/queue')[0],403)
        self.assertIn('Stufe 1'.encode(),self.request('/overview')[1])
        self.assertEqual(self.request('/demo-role',{'csrf':csrf,'role':'judge'})[0],303)
        self.assertEqual(self.request('/case/DEMO-00003')[0],200)

    def test_help_privacy_and_planning_pages(self):
        status, page = self.request('/privacy')
        self.assertEqual(status,200)
        self.assertIn('Wer sieht was'.encode(),page)
        self.login('worker')
        guide = self.request('/help')[1]
        self.assertIn(b'href="/overview"',guide)
        self.assertNotIn(b'href="/forecast">',guide)
        self.assertEqual(self.request('/language/en?view=/privacy')[0],303)
        self.assertIn(b'Who sees what',self.request('/privacy')[1])
        self.cookies.clear()
        self.login('judging')
        plan = self.request('/forecast?rate_a1=1000&rate_work=0&rate_household=0')[1]
        for anchor in (b'id="payments"',b'id="scenario"',b'id="zemis"',b'id="arrivals"',b'state=record',b'state=zemis'):
            self.assertIn(anchor,plan)
        self.assertRegex(plan.decode(),r'<strong>CHF \d+’000</strong>')
        self.assertEqual(self.request('/queue?state=zemis')[0],200)
        self.assertIn(b'case-link',self.request('/queue?state=record')[1])
        self.cookies.clear()
        self.login('manager')
        plan = self.request('/forecast')[1]
        self.assertIn(b'id="zemis"',plan)
        self.assertNotIn(b'state=zemis',plan)

    def test_demo_personas_apply_backend_permissions_and_preserve_locale_context(self):
        self.server.hosted = True
        try:
            csrf = self.login('judging')
            self.assertEqual(self.request('/demo-role',{'csrf':csrf,'role':'worker'})[0],303)
            self.assertEqual(self.request('/case/DEMO-00001')[0],200)
            self.assertEqual(self.request('/case/DEMO-00003')[0],404)
            self.assertEqual(self.request('/language/fr-CH?view=queue&state=risk')[0],303)
            self.assertIn(b'value="risk" selected',self.request('/queue?state=risk')[1])
            self.assertEqual(self.request('/forecast')[0],403)
            self.assertEqual(self.request('/demo-role',{'csrf':csrf,'role':'manager'})[0],303)
            self.assertEqual(self.request('/queue')[0],403)
            self.assertIn('Tendance mensuelle A1'.encode(),self.request('/overview')[1])
            self.assertEqual(self.request('/demo-role',{'csrf':csrf,'role':'importer'})[0],303)
            self.assertEqual(self.request('/export')[0],403)
            self.assertEqual(self.request('/quality')[0],200)
            self.assertEqual(self.request('/demo-role',{'csrf':csrf,'role':'judge'})[0],303)
            self.assertEqual(self.request('/export')[0],200)
            self.cookies.clear()
            csrf = self.login('worker')
            self.assertEqual(self.request('/demo-role',{'csrf':csrf,'role':'judge'})[0],403)
        finally:
            self.server.hosted = False

    def test_assistant_rejects_canary_without_reflection_and_limits_aggregate_roles(self):
        canary = b'PRIVATE-PHASE8-CANARY'
        self.login('judging')
        for param in ('q','topic','intent','asof'):
            status, body = self.request('/ai?'+urlencode({param:canary.decode()}))
            self.assertEqual(status,400)
            self.assertNotIn(canary,body)
        db = data.connect(self.path)
        try:
            self.assertFalse(any(canary.decode() in ' '.join(row) for row in db.execute('SELECT * FROM audit')))
        finally:
            db.close()
        status, page = self.request('/ai?topic=scenario2027&intent=monthly_change')
        self.assertEqual(status,200)
        self.assertIn(b'2027-01-01',page)
        self.assertIn(b'2026-09-30',page)
        self.assertIn(b'+6',page)
        self.cookies.clear()
        self.login('worker')
        status, page = self.request('/ai?intent=monthly_change')
        self.assertEqual(status,200)
        self.assertNotIn(b'+2',page)

    def test_three_languages_and_monthly_reimport(self):
        csrf=self.login('judging')
        for language,word in [('de-CH','Übersicht'),('en','Overview'),('fr-CH','Vue d’ensemble')]:
            self.assertEqual(self.request('/language/'+language+'?view=reports')[0],303)
            self.assertIn(word.encode(),self.request('/overview')[1])
            for path in ('/queue','/reports','/ai','/forecast','/intake','/export'):
                self.assertEqual(self.request(path)[0],200)
        self.assertEqual(self.request('/seed',{'csrf':csrf,'date':data.MONTHS[0]})[0],303)
        self.assertIn(b'30.09.2026',self.request('/case/DEMO-00001')[1])
        self.assertEqual(self.request('/seed',{'csrf':csrf,'date':data.MONTHS[1]})[0],303)
        october = self.request('/case/DEMO-00001')[1]
        self.assertIn(b'12.10.2026',october)
        self.assertIn(b'Sprachstand',october)
        db=data.connect(self.path)
        with db:
            db.execute('UPDATE sessions SET expires=0 WHERE username="judging"')
        db.close()
        self.assertEqual(self.request('/export')[0],303)
