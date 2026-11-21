"""Measure authenticated load and backup recovery against an isolated loopback app."""
from argparse import ArgumentParser
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, closing
from io import BytesIO
from math import ceil
from pathlib import Path
from statistics import median
from tempfile import TemporaryDirectory
from threading import Barrier, Thread
from time import perf_counter
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener
from urllib.error import HTTPError
from http.cookiejar import CookieJar
from zipfile import ZipFile
import json
import secrets

from . import data
from .server import App, account
from .smoke import NoRedirect, csrf


@contextmanager
def running(path):
    with App(('127.0.0.1',0),path,False) as server:
        thread = Thread(target=server.serve_forever,kwargs={'poll_interval':0.02},daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}'
        finally:
            server.shutdown()
            thread.join()


class Client:
    def __init__(self, origin):
        self.origin = origin
        self.opener = build_opener(NoRedirect(),HTTPCookieProcessor(CookieJar()))

    def request(self,path,expected=200,fields=None):
        body = urlencode(fields).encode() if fields is not None else None
        start = perf_counter()
        try:
            response = self.opener.open(Request(self.origin+path,data=body),timeout=30)
        except HTTPError as exc:
            response = exc
        with closing(response):
            output = response.read()
            if response.status!=expected:
                raise RuntimeError(f'{path} returned {response.status}, expected {expected}')
        return output,(perf_counter()-start)*1000

    def login(self,password):
        token = csrf(self.request('/login')[0])
        self.request('/login',303,{'csrf':token,'username':'bench','password':password})
        return csrf(self.request('/reports')[0])


def rates(results):
    samples = defaultdict(list)
    for result in results:
        for route,value in result:
            samples[route].append(value)
    return {key:{'requests':len(values),'p50_ms':round(median(values),2),
                 'p95_ms':round(sorted(values)[ceil(len(values)*.95)-1],2),'max_ms':round(max(values),2)}
            for key,values in sorted(samples.items())}


def workbook(output,proof=None):
    with ZipFile(BytesIO(output)) as archive:
        sheet = archive.read('xl/worksheets/sheet3.xml')
        if archive.testzip() is not None or b'DEMO-00001' not in sheet or proof and proof not in sheet:
            raise RuntimeError('Unexpected workbook or recovery evidence')


def exercise(workers=8,rounds=3,people=1000):
    with TemporaryDirectory() as directory:
        source, target = (Path(directory)/name for name in ('source.sqlite','recovered.sqlite'))
        password = secrets.token_urlsafe(20)
        with closing(data.connect(source)) as db:
            snapshots = [data.load_files(db,data.seed(month,people).values(),month,'synthetic')[0] for month in data.MONTHS]
            account(db,'bench',password,'judge')
        load_start = perf_counter()
        with running(source) as origin:
            clients = [Client(origin) for _ in range(workers)]
            tokens = [c.login(password) for c in clients]
            barrier = Barrier(workers+1,timeout=30)

            def act(index):
                client,token = clients[index],tokens[index]
                side = index%2
                expected = (b'2026-09-30',b'2026-10-31')[side]
                barrier.wait()
                observed = []
                for _ in range(rounds):
                    _, duration = client.request('/snapshot',303,{'csrf':token,'id':snapshots[side]})
                    observed.append(('snapshot_select',duration))
                    for route in ('/overview','/queue','/case/DEMO-00001','/export'):
                        content,duration = client.request(route)
                        if route=='/export':
                            workbook(content,b'2026-10-12' if side else None)
                            if not side:
                                with ZipFile(BytesIO(content)) as exported:
                                    first = exported.read('xl/worksheets/sheet3.xml').split(b'</row>',2)[1]
                                if b'2026-10-12' in first:
                                    raise RuntimeError('October proof appeared in September export')
                        elif expected not in content:
                            raise RuntimeError('Snapshot state crossed sessions')
                        observed.append((route,duration))
                return observed

            with ThreadPoolExecutor(max_workers=workers) as pool:
                jobs = [pool.submit(act,i) for i in range(workers)]
                barrier.wait()
                copy_start = perf_counter()
                with closing(data.connect(source)) as db:
                    data.backup(db,target)
                backup_seconds = perf_counter()-copy_start
                observed = [job.result() for job in jobs]
            retained, _ = clients[0].request('/export')
            clients[0].request('/seed-invalid',422,{'csrf':tokens[0],'date':data.MONTHS[1]})
            after,_ = clients[0].request('/export')
            if after!=retained:
                raise RuntimeError('Rejected import changed selected results')
        elapsed = perf_counter()-load_start

        restore_start = perf_counter()
        with closing(data.connect(target)) as recovered:
            if recovered.execute('PRAGMA quick_check').fetchone()[0]!='ok':
                raise RuntimeError('Recovery integrity check failed')
            if recovered.execute('SELECT count(*) FROM snapshots').fetchone()[0]!=len(snapshots):
                raise RuntimeError('Backup did not preserve both accepted snapshots')
            revoked = data.revoke_sessions(recovered)
        with running(target) as origin:
            clients[0].origin = origin
            clients[0].request('/export',303)
            verify = Client(origin)
            verify.request('/export',303)
            verify.login(password)
            output,_ = verify.request('/export')
            workbook(output,b'2026-10-12')
            recovered_seconds = perf_counter()-restore_start
        return {'people_per_snapshot':people,'concurrent_sessions':workers,'rounds':rounds,
                'measured_requests':sum(len(v) for v in observed),'request_errors':0,
                'endpoint_latency':rates(observed),'load_and_login_seconds':round(elapsed,3),
                'backup_seconds_during_load':round(backup_seconds,3),'backup_bytes':target.stat().st_size,
                'restore_to_verified_export_seconds':round(recovered_seconds,3),
                'restored_sessions_revoked':revoked,'rejected_import_preserved_export':True}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--workers',type=int,default=8,choices=range(2,9))
    parser.add_argument('--rounds',type=int,default=3)
    parser.add_argument('--people',type=int,default=1000)
    args = parser.parse_args()
    if not 1<=args.rounds<=20 or not 144<=args.people<=10000:
        parser.error('Use 1–20 rounds and 144–10,000 synthetic people')
    print(json.dumps(exercise(args.workers,args.rounds,args.people),indent=2))


if __name__=='__main__':
    main()
