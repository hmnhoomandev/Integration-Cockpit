from pathlib import Path
from shutil import which
from unittest import TestCase, skipUnless
from sys import platform

from cockpit.intake import suggest
from cockpit.insights import read_aggregate_series, observations


def pdf(lines):
    contents = 'BT /F1 12 Tf 50 740 Td\n'+'\n'.join(f'({line}) Tj 0 -18 Td' for line in lines)+'\nET\n'
    objects = [
       b'<< /Type /Catalog /Pages 2 0 R >>',
       b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
       b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
       f'<< /Length {len(contents)} >>\nstream\n{contents}endstream'.encode(),
       b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    blob = bytearray(b'%PDF-1.4\n')
    offsets = []
    for i,obj in enumerate(objects,1):
        offsets.append(len(blob))
        blob.extend(f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n')
    xref=len(blob)
    blob.extend(f'xref\n0 {len(objects)+1}\n0000000000 65535 f \n'.encode())
    for offset in offsets:
        blob.extend(f'{offset:010d} 00000 n \n'.encode())
    blob.extend(f'trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(blob)


@skipUnless(which('pdftotext') or (platform=='darwin' and which('osascript')), 'local PDF extractor')
class IntakeTests(TestCase):
    def test_filled_pdf_and_private_narrative(self):
        payload = pdf(['ZEMIS: SYN-Z00001','childcare scheduling','CANARY-PRIVATE-NARRATIVE'])
        result = suggest(payload,{'SYN-Z00001':'DEMO-00001'})
        self.assertEqual(result,{'mode':'review','person':'DEMO-00001','suggestions':['scheduling']})
        self.assertEqual(suggest(payload,{})['mode'],'manual')
        self.assertEqual(suggest(pdf([]),{'SYN-Z00001':'DEMO-00001'})['mode'],'manual')


class SeriesTests(TestCase):
    def test_aggregate_csv_and_invalid_fields(self):
        values=observations()
        csv='month,count\n'+'\n'.join(f'{2022+i//12}-{i%12+1:02d},{n}' for i,n in enumerate(values))
        self.assertEqual([row[1] for row in read_aggregate_series(csv.encode())],values)
        with self.assertRaises(ValueError):
            read_aggregate_series(csv.replace('2022-02','2022-03').encode())
        with self.assertRaises(ValueError):
            read_aggregate_series((csv+'\nCANARY-PERSON,5').encode())
