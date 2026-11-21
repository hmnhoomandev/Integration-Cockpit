"""Local PDF text extraction with optional bounded OCR."""
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .insights import IntakeQuestion, gateway

HEADER = re.compile(r'^\s*ZEMIS(?:[- ]Nr\.?| Nummer)?\s*:\s*([A-Za-z0-9-]{1,35})\s*$',re.M|re.I)
PHRASES = {
    'scheduling': ('childcare scheduling','kinderbetreuung','horaires de garde'),
    'course': ('course participation','kursteilnahme','participation à un cours'),
    'schooling': ('prior schooling','schulbildung','scolarité antérieure'),
    'housing': ('housing stability','wohnstabilität','stabilité du logement'),
}


def run_text(command, timeout):
    process = subprocess.run(command,timeout=timeout,capture_output=True,check=True)
    return process.stdout[:50_000].decode('utf-8','replace')


def text_layer(path):
    tool = shutil.which('pdftotext')
    if tool:
        return run_text([tool,'-f','1','-l','12',str(path),'-'],8)
    jxa = shutil.which('osascript') if sys.platform=='darwin' else None
    if jxa:
        return run_text([jxa,'-l','JavaScript',str(Path(__file__).with_name('pdfkit.js')),str(path)],8)
    return ''


def scan(path):
    renderer = shutil.which('pdftoppm')
    ocr = shutil.which('tesseract')
    if not renderer or not ocr:
        return None
    prefix = path.parent/'scan'
    run_text([renderer,'-f','1','-l','3','-r','180','-scale-to','1800','-png',str(path),str(prefix)],10)
    languages = set(run_text([ocr,'--list-langs'],4).splitlines())
    selected = '+'.join(language for language in ('eng','deu','fra') if language in languages)
    if not selected:
        return None
    return '\n'.join(run_text([ocr,str(image),'stdout','-l',selected,'--psm','6'],5)
                     for image in sorted(path.parent.glob('scan-*.png')))


def identities(text):
    return set(HEADER.findall('\n'.join(text.splitlines()[:35])))


def suggest(blob, authorized_ids):
    if len(blob)>2_000_000 or not blob.startswith(b'%PDF-'):
        return {'mode':'manual','reason':'invalid_pdf'}
    with TemporaryDirectory() as directory:
        source = Path(directory)/'input.pdf'
        source.write_bytes(blob)
        try:
            text = text_layer(source)
            matches = identities(text)
            extraction = 'text'
            if not matches and len(text.strip()) < 60:
                extracted = scan(source)
                if extracted:
                    text = extracted
                    matches = identities(text)
                    extraction = 'ocr'
        except (subprocess.SubprocessError,OSError):
            return {'mode':'manual','reason':'unreadable'}
    if len(matches)!=1 or not matches <= authorized_ids.keys():
        return {'mode':'manual','reason':'unlinked'}
    match = next(iter(matches))
    normalized = text.casefold()
    suggestions = [gateway(IntakeQuestion(key))['category']
                   for key,phrases in PHRASES.items() if any(phrase in normalized for phrase in phrases)]
    result = {'mode':'review','person':authorized_ids[match],'suggestions':suggestions,'text':text}
    if extraction=='ocr':
        result['extraction'] = extraction
    return result
