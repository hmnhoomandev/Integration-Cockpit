"""Bounded OOXML reader and portable workbook writer."""
from datetime import date, timedelta
from html import escape
from math import isfinite
from io import BytesIO
from itertools import chain, islice
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


class Cell:
    """A value with a named style from STYLES."""
    __slots__ = ('value','style')

    def __init__(self, value, style):
        self.value, self.style = value, style


# Fills and fonts follow the cockpit lights; every state cell also carries a symbol and text.
STATE_COLOURS = {'achieved':('E2F2E9','1D6B45'),'ontrack':('FFF4C7','7A5B00'),'risk':('FCE3DC','9C2E14'),
                 'overdue':('F6CFCB','8E1C14'),'late':('F6CFCB','8E1C14'),'review':('ECE6F8','57409A'),'na':('EFEAE3','6D625B')}
STYLES = ['default','header','date','bold',*('state_'+k for k in STATE_COLOURS)]
EPOCH = date(1899,12,30)


def serial(value):
    return (value-EPOCH).days


def styles_xml():
    fills = ['<fill><patternFill patternType="none"/></fill>','<fill><patternFill patternType="gray125"/></fill>',
             '<fill><patternFill patternType="solid"><fgColor rgb="FF16110F"/></patternFill></fill>']
    fonts = ['<font><sz val="11"/><name val="Calibri"/></font>','<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>',
             '<font><b/><sz val="11"/><name val="Calibri"/></font>']
    xfs = ['<xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>',
           '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>',
           '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" applyNumberFormat="1"/>',
           '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" applyFont="1"/>']
    for fill,font in STATE_COLOURS.values():
        fills.append(f'<fill><patternFill patternType="solid"><fgColor rgb="FF{fill}"/></patternFill></fill>')
        fonts.append(f'<font><b/><sz val="11"/><color rgb="FF{font}"/><name val="Calibri"/></font>')
        xfs.append(f'<xf numFmtId="0" fontId="{len(fonts)-1}" fillId="{len(fills)-1}" borderId="0" applyFont="1" applyFill="1"/>')
    return (f'<styleSheet xmlns="{NS}"><numFmts count="1"><numFmt numFmtId="164" formatCode="dd.mm.yyyy"/></numFmts>'
            f'<fonts count="{len(fonts)}">{"".join(fonts)}</fonts><fills count="{len(fills)}">{"".join(fills)}</fills>'
            '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            f'<cellXfs count="{len(xfs)}">{"".join(xfs)}</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>')


def write(tabs):
    def entry(name):
        info = ZipInfo(name)
        info.compress_type = ZIP_DEFLATED
        return info
    def cell(address, value, style):
        if isinstance(value,Cell):
            value, style = value.value, value.style
        if value is None:
            return f'<c r="{address}" s="{STYLES.index(style)}"/>' if style!='default' else ''
        if isinstance(value,date):
            value, style = serial(value), ('date' if style=='default' else style)
        index = STYLES.index(style)
        if type(value) in (int,float):
            return f'<c r="{address}" s="{index}" t="n"><v>{value}</v></c>'
        value = escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]','',str(value)))
        return f'<c r="{address}" s="{index}" t="inlineStr"><is><t xml:space="preserve">{value}</t></is></c>'
    out = BytesIO()
    with ZipFile(out,'w',ZIP_DEFLATED) as z:
        entries = list(tabs.items())
        z.writestr(entry('[Content_Types].xml'), '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' + ''.join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for i in range(1,len(entries)+1)) + '</Types>')
        z.writestr(entry('_rels/.rels'),f'<Relationships xmlns="{PKG}"><Relationship Id="rId1" Type="{REL}/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        z.writestr(entry('xl/_rels/workbook.xml.rels'),f'<Relationships xmlns="{PKG}">'+''.join(f'<Relationship Id="rId{i}" Type="{REL}/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1,len(entries)+1))
                   +f'<Relationship Id="rId{len(entries)+1}" Type="{REL}/styles" Target="styles.xml"/></Relationships>')
        z.writestr(entry('xl/workbook.xml'),f'<workbook xmlns="{NS}" xmlns:r="{REL}"><sheets>'+''.join(f'<sheet name="{escape(name,quote=True)}" sheetId="{i}" r:id="rId{i}"/>' for i,(name,_) in enumerate(entries,1))+'</sheets></workbook>')
        z.writestr(entry('xl/styles.xml'),styles_xml())
        for i,(_,rows) in enumerate(entries,1):
            with z.open(entry(f'xl/worksheets/sheet{i}.xml'),'w') as sheet:
                rows = iter(rows)
                head = next(rows,None)
                width = max(1,len(head or ()))
                # Column widths come from the first rows only, so large sheets still stream.
                sample = list(islice(rows,50))
                rows = chain(sample,rows)
                def size(value):
                    value = getattr(value,'value',value)
                    return 10 if isinstance(value,date) else len(str(value)) if value is not None else 0
                widths = ''.join(f'<col min="{c}" max="{c}" width="{max(10,min(70,max(size(r[c-1]) for r in [head,*sample] if len(r)>=c)+3))}" customWidth="1"/>'
                                 for c in range(1,len(head or ())+1))
                sheet.write((f'<worksheet xmlns="{NS}"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
                             +(f'<cols>{widths}</cols>' if widths else '')+'<sheetData>').encode())
                number = 0
                for number, row in enumerate(chain([head] if head is not None else [],rows),1):
                    if number > 1048576:
                        raise ValueError('worksheet_row_limit')
                    style = 'header' if number==1 else 'default'
                    cells = ''.join(cell(letters(column)+str(number),value,style) for column,value in enumerate(row,1))
                    sheet.write((f'<row r="{number}">'+cells+'</row>').encode())
                sheet.write(f'</sheetData><autoFilter ref="A1:{letters(width)}{max(1,number)}"/></worksheet>'.encode())
    return out.getvalue()
