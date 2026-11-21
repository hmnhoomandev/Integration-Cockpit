"""Local masking of personal data before any text reaches a language model.

Runs before every AI request. If anything is still detected after masking, the request is refused.
"""
import re

# Order matters: specific identifiers first so a looser pattern cannot swallow them.
PATTERNS = (
    ('ahv',re.compile(r'\b756[.\s]?\d{4}[.\s]?\d{4}[.\s]?\d{2}\b')),
    ('iban',re.compile(r'\bCH\d{2}(?:\s?[0-9A-Z]{4}){4}\s?[0-9A-Z]{1}\b',re.I)),
    ('email',re.compile(r'\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b')),
    ('phone',re.compile(r'(?:\+41|0041|\b0)\s?\(?\d{2}\)?[\s./-]?\d{3}[\s./-]?\d{2}[\s./-]?\d{2}\b')),
    ('case_id',re.compile(r'\b(?:DEMO|SYN-[HZ])-?\d{3,}\b|\bZEMIS(?:[- ]?(?:Nr\.?|Nummer))?\s*:\s*[A-Za-z0-9-]{4,}|\bZEMIS[- ]?(?:Nr\.?|Nummer)\s+[A-Za-z0-9-]{4,}',re.I)),
    ('number',re.compile(r'\b\d{6,}\b')),
    ('date',re.compile(r'\b\d{1,2}\.\d{1,2}\.(?:19|20)\d{2}\b|\b(?:19|20)\d{2}-\d{2}-\d{2}\b')),
    ('address',re.compile(r'\b[A-ZÄÖÜ][a-zäöüß]+(?:strasse|gasse|weg|platz|rain|halde|allee|str\.)\s*\d+[a-z]?\b'
                          r'|\b(?:rue|chemin|avenue|route)\s+[^\n,]{2,40}?\d+\b|\b[1-9]\d{3}\s+[A-ZÄÖÜ][a-zäöü]+\b')),
    ('name',re.compile(r'(?:(?<=Name:)|(?<=Vorname:)|(?<=Nachname:)|(?<=Nom:)|(?<=Prénom:))[ \t]*[A-ZÄÖÜÉÈ][^\n,;]{1,60}'
                       r'|\b(?:Herr|Frau|Hr\.|Fr\.|Monsieur|Madame|Mr\.|Mrs\.|Ms\.)\s+[A-ZÄÖÜ][\w-]+(?:\s+[A-ZÄÖÜ][\w-]+)?')),
)
LABELS = {'ahv':'AHV','iban':'IBAN','email':'E-MAIL','phone':'TELEFON','case_id':'ID','number':'NUMMER',
          'date':'DATUM','address':'ADRESSE','name':'NAME'}


def mask(text, extra=()):
    """Masked text and the number of hits per category. `extra` are known values such as identifiers."""
    counts = {}
    for value in sorted({v for v in extra if v and len(v)>=3},key=len,reverse=True):
        hits = text.count(value)
        if hits:
            text = text.replace(value,'[ID]')
            counts['case_id'] = counts.get('case_id',0)+hits
    for key,pattern in PATTERNS:
        text,hits = pattern.subn(lambda m:(' ' if m.group(0).startswith(' ') else '')+f'[{LABELS[key]}]',text)
        if hits:
            counts[key] = counts.get(key,0)+hits
    return text,counts


def leaks(text):
    """Categories still detectable in text that is about to leave the machine."""
    text = re.sub(r'\[[A-Z-]+\]','',text)
    return [key for key,pattern in PATTERNS if key!='number' and pattern.search(text)]
