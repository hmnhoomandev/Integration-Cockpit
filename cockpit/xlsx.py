"""Bounded OOXML reader and portable workbook writer."""
from datetime import date, timedelta
from html import escape
from math import isfinite
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import re

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'


def letters(number):
    value = ''
    while number:
        number, remainder = divmod(number - 1, 26)
        value = chr(65 + remainder) + value
    return value


def read(blob):
    if len(blob) > 20_000_000:
        raise ValueError('file_size')
    with ZipFile(BytesIO(blob)) as archive:
        files = archive.infolist()
        if len(files) > 200 or sum(f.file_size for f in files) > 100_000_000:
            raise ValueError('archive_size')
        if any(re.search(r'externalLinks|vbaProject|/embeddings/', f.filename, re.I) for f in files):
            raise ValueError('active_content')
        def xml(name):
            raw = archive.read(name)
            if b'\x00' in raw or re.search(rb'<!DOCTYPE|<!ENTITY', raw, re.I):
                raise ValueError('xml_declaration')
            return ET.fromstring(raw)
        workbook = xml('xl/workbook.xml')
        sheets = workbook.findall('.//{*}sheet')
        if len(sheets) != 1:
            raise ValueError('expected_one_sheet')
        links = xml('xl/_rels/workbook.xml.rels')
        target = next((x.get('Target','') for x in links if x.get('Id') == sheets[0].get('{'+REL+'}id')), '')
        path = target.lstrip('/') if target.startswith('/') else str(PurePosixPath('xl') / target)
        if not re.fullmatch(r'xl/worksheets/[^/]+\.xml', path):
            raise ValueError('worksheet_target')
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings = [''.join(t.text or '' for t in e.iter('{'+NS+'}t')) for e in xml('xl/sharedStrings.xml')]
        props = workbook.find('{*}workbookPr')
        mac = props is not None and props.get('date1904') in ('1','true')
        with archive.open(path) as sheet:
            yield from sheet_rows(sheet, strings, mac)


class SafeXML:
    def __init__(self, stream):
        self.stream = stream
        self.tail = b''

    def read(self, size):
        data = self.stream.read(size)
        if b'\x00' in data or re.search(rb'<!DOCTYPE|<!ENTITY', self.tail + data, re.I):
            raise ValueError('xml_declaration')
        self.tail = data[-12:] if len(data) >= 12 else (self.tail + data)[-12:]
        return data


def sheet_rows(sheet, strings, mac):
    stack = []
    index = 0
    for event, row in ET.iterparse(SafeXML(sheet), events=('start','end')):
        if event == 'start':
            if row.tag == '{'+NS+'}f':
                raise ValueError('formula')
            stack.append(row)
            continue
        stack.pop()
        if row.tag == '{'+NS+'}row' and stack and stack[-1].tag == '{'+NS+'}sheetData':
            index += 1
            if index > 300_001:
                raise ValueError('row_limit')
            parent = stack[-1]
            values = {}
            for cell in row.findall('{*}c'):
                address = cell.get('r','')
                match = re.fullmatch(r'([A-Z]{1,3})[0-9]+', address)
                if not match:
                    raise ValueError('cell_address')
                pos = 0
                for character in match[1]:
                    pos = pos * 26 + ord(character) - 64
                kind = cell.get('t','n')
                val = cell.findtext('{*}v')
                if kind == 'inlineStr':
                    val = ''.join(node.text or '' for node in cell.findall('.//{*}t'))
                elif kind == 's' and val is not None:
                    val = strings[int(val)]
                elif kind == 'n' and val:
                    val = float(val)
                    if not isfinite(val):
                        raise ValueError('invalid_number')
                elif kind == 'd' and val:
                    val = val.split('T')[0]
                values[pos] = val
            result = int(row.get('r',index)), [values.get(i) for i in range(1,max(values,default=0)+1)], mac
            parent.remove(row)
            row.clear()
            yield result


def excel_date(value, mac=False):
    if value in (None,''):
        return None
    if isinstance(value,(float,int)):
        if value < 1 or value > 100_000 or value != int(value) or (not mac and value == 60):
            raise ValueError('invalid_date')
        base = date(1904,1,1) if mac else date(1899,12,31)
        return base + timedelta(days=int(value) - int(not mac and value > 60))
    if re.fullmatch(r'\d{2}\.\d{2}\.\d{4}',value):
        day, month, year = value.split('.')
        value = f'{year}-{month}-{day}'
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):
        raise ValueError('invalid_date')
    return date.fromisoformat(value)


def write(tabs):
    def entry(name):
        info = ZipInfo(name)
        info.compress_type = ZIP_DEFLATED
        return info
    out = BytesIO()
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        entries = list(tabs.items())
        z.writestr(entry('[Content_Types].xml'), '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(entries)+1)) + '</Types>')
        z.writestr(entry('_rels/.rels'),f'<Relationships xmlns="{PKG}"><Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr(entry('xl/_rels/workbook.xml.rels'),f'<Relationships xmlns="{PKG}">'+''.join(f'<Relationship Id="rId{i}" Type="{REL}/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(entries)+1))+'</Relationships>')
        z.writestr(entry('xl/workbook.xml'),f'<workbook xmlns="{NS}" xmlns:r="{REL}"><sheets>'+''.join(f'<sheet name="{escape(name,quote=True)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_) in enumerate(entries,1))+'</sheets></workbook>')
        for i,(_,rows) in enumerate(entries,1):
            with z.open(entry(f'xl/worksheets/sheet{i}.xml'),'w') as sheet:
                sheet.write(f'<worksheet xmlns="{NS}"><sheetData>'.encode())
                width = 1
                number = 0
                for number, row in enumerate(rows,1):
                    if number > 1048576:
                        raise ValueError('worksheet_row_limit')
                    if number == 1:
                        width = max(1,len(row))
                    cells = []
                    for column,value in enumerate(row,1):
                        address = letters(column) + str(number)
                        if value is None:
                            continue
                        if type(value) in (int,float):
                            cells.append(f'<c r="{address}" t="n"><v>{value}</v></c>')
                        else:
                            value = escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',str(value)))
                            cells.append(f'<c r="{address}" t="inlineStr"><is><t xml:space="preserve">{value}</t></is></c>')
                    sheet.write((f'<row r="{number}">'+''.join(cells)+'</row>').encode())
                sheet.write(f'</sheetData><autoFilter ref="A1:{letters(width)}{max(1,number)}"/></worksheet>'.encode())
    return out.getvalue()
