"""Verify an authorized cockpit deployment without writing credentials to output."""
from argparse import ArgumentParser
from contextlib import closing
from getpass import getpass
from http.cookiejar import CookieJar
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener
from zipfile import ZipFile
import re

from .data import MONTHS


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def csrf(html):
    token = re.search(rb'name="csrf" value="([A-Za-z0-9_-]+)"', html)
    require(token is not None, 'CSRF form token missing')
    return token[1].decode()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify(base, username, password):
    opener = build_opener(NoRedirect(), HTTPCookieProcessor(CookieJar()))

    def request(path, fields=None):
        body = urlencode(fields).encode() if fields is not None else None
        try:
            response = opener.open(Request(base + path, data=body), timeout=15)
        except HTTPError as error:
            response = error
        with closing(response):
            return response.status, response.headers, response.read()

    require(request('/health')[2] == b'ok', 'Health check failed')
    for path in ('/overview', '/export', '/case/DEMO-00001'):
        status, headers, _ = request(path)
        require(status == 303 and headers.get('Location') == '/login', f'Anonymous access gate failed on {path}')
    status, _, login = request('/login')
    require(status == 200, 'Sign-in page failed')
    status, _, _ = request('/login', {'username': username, 'password': password, 'csrf': csrf(login)})
    require(status == 303, 'Sign-in failed')
    try:
        for locale, heading in [('de-CH','Übersicht'), ('fr-CH','Vue d’ensemble'), ('en','Overview')]:
            require(request(f'/language/{locale}?view=overview')[0] == 303, f'Locale switch failed for {locale}')
            status, _, page = request('/overview')
            require(status == 200 and f'<h1>{heading}</h1>'.encode() in page, f'Overview failed for {locale}')
        status, _, reports = request('/reports')
        require(status == 200, 'Reports page failed')
        form_token = csrf(reports)
        for month, proof in zip(MONTHS, (b'Check certificate or schooling evidence', b'12.10.2026'), strict=True):
            status, _, _ = request('/seed', {'csrf': form_token, 'date': month})
            require(status == 303, 'Synthetic snapshot replay failed')
            status, _, case = request('/case/DEMO-00001')
            require(status == 200 and proof in case, f'Unexpected A1 evidence for {month}')
        status, headers, workbook = request('/export')
        require(status == 200 and 'spreadsheetml' in headers.get('Content-Type',''), 'Excel download failed')
        with ZipFile(BytesIO(workbook)) as archive:
            require(archive.testzip() is None, 'Workbook ZIP integrity failed')
            details = archive.read('xl/worksheets/sheet3.xml')
            require(b'DEMO-00001' in details and b'<v>46307</v>' in details, 'Workbook evidence missing')
        status, _, _ = request('/seed-invalid', {'csrf':form_token,'date':MONTHS[0]})
        require(status==422, 'Incomplete import was not rejected')
        require(request('/export')[2]==workbook, 'Rejected import changed the selected results')
        status, _, quality = request('/quality')
        require(status==200, 'Import quality workbook failed')
        with ZipFile(BytesIO(quality)) as archive:
            require(b'missing_source' in archive.read('xl/worksheets/sheet3.xml'), 'Missing source diagnosis absent')
            require(b'SHA-256' in archive.read('xl/worksheets/sheet2.xml'), 'Source fingerprint column absent')
        require(request('/ai')[0] == 200, 'Rules assistant failed')
        require(request('/forecast')[0] == 200, 'Forecast failed')
    finally:
        status, _, page = request('/reports')
        if status == 200:
            request('/logout', {'csrf': csrf(page)})
    require(request('/export')[0] == 303, 'Export accessible after sign-out')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('url', help='HTTPS origin or localhost URL')
    parser.add_argument('username')
    args = parser.parse_args()
    url = urlsplit(args.url)
    if (not url.hostname or url.username or url.password or url.path not in ('','/') or url.query or url.fragment
        or (url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('127.0.0.1','localhost','::1')))):
        parser.error('Enter an HTTPS origin or a local HTTP origin without credentials or path')
    verify(args.url.rstrip('/'), args.username, getpass())
    print('Verified health, sign-in, locales, monthly replay, rejected import, quality report, A1 evidence, Excel, assistant, forecast, and sign-out.')


if __name__ == '__main__':
    main()
