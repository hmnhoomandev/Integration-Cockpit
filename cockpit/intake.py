"""Restricted local extraction via PDFKit on macOS or pdftotext."""
import re
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from .insights import IntakeQuestion, gateway


def suggest(blob, authorized_ids):
    if len(blob)>2_000_000 or not blob.startswith(b'%PDF-'):
        return {'mode':'manual','reason':'invalid_pdf'}
    tool = shutil.which('pdftotext')
    jxa = shutil.which('osascript') if sys.platform=='darwin' else None
    if not tool and not jxa:
        return {'mode':'manual','reason':'missing_extractor'}
    with TemporaryDirectory() as directory:
        source = Path(directory)/'input.pdf'
        source.write_bytes(blob)
        cmd = [tool,'-f','1','-l','12',str(source),'-'] if tool else [
            jxa,'-l','JavaScript',str(Path(__file__).with_name('pdfkit.js')),str(source)]
        try:
            process = subprocess.run(cmd,timeout=8,capture_output=True,check=True)
        except (subprocess.SubprocessError,OSError):
            return {'mode':'manual','reason':'unreadable'}
    text = process.stdout[:50_000].decode('utf-8','replace')
    match = re.search(r'^\s*ZEMIS(?:[- ]Nr\.?| Nummer)?\s*:\s*([A-Za-z0-9-]{1,35})\s*$', '\n'.join(text.splitlines()[:35]),re.M|re.I)
    if not match or match[1] not in authorized_ids:
        return {'mode':'manual','reason':'unlinked'}
    categories = {'childcare scheduling':'scheduling','course participation':'course',
                  'prior schooling':'schooling','housing stability':'housing'}
    suggestions = [gateway(IntakeQuestion(key))['category'] for phrase,key in categories.items() if phrase in text.casefold()]
    return {'mode':'review','person':authorized_ids[match[1]],'suggestions':suggestions}
