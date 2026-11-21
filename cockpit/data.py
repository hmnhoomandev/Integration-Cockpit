"""Source contracts, deterministic fixtures and transactional snapshot storage."""
from collections import defaultdict
from contextlib import closing
from datetime import date, timedelta, datetime, timezone
from hashlib import sha256
from pathlib import Path
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError
import json
import sqlite3
import unicodedata

from . import xlsx

SCHEMA = json.loads(Path(__file__).with_name('schema.json').read_text())
DATES = {
    'clients': ('Zuständigkeitsbeginn','Zuständigkeitsende','Datum Übergang Gemeindezuständigkeit','Geburtsdatum'),
    'events': ('Ereignisdatum','Erledigungsdatum'),
    'status': ('Verfahrensstand Gültig ab','Verfahrensstand Gültig bis'),
    'membership': ('Dossierperson Von','Dossierperson Bis'),
    'work': ('Von','Bis'), 'support': ('Finanzielle Unterstützung Gültig von','Finanzielle Unterstützung Gültig bis'),
    'education': ('Start','Abschluss'), 'official': ('Erreicht am',), 'language': ('Datum Erreichung',),
    'housing': ('Unterbringung Von','Unterbringung Bis'), 'zemis': ('Arbeitsbeginn','Verpflichtet bis'),
}
IDS = ('Klientennummer','Zemis Nummer','Klient/-in Zemis-Nr.','Dossier-Nr.')
PAIR = {'status': DATES['status'], 'membership': DATES['membership'], 'work': DATES['work'], 'support': DATES['support'],
        'education': DATES['education'], 'housing': DATES['housing'], 'zemis': DATES['zemis'],
        'clients': DATES['clients'][:2]}
MONTHS = ('2026-09-30','2026-10-31')
PHASE4_MONTH = '2026-08-31'
PHASE5_MONTH = '2026-07-31'



def norm(value):
    return ' '.join(unicodedata.normalize('NFC',value).split()) if isinstance(value,str) else value


def seed(asof, size=None):
    """Demo months get the story caseload; other dates and explicit sizes keep the regular test grid."""
    if asof in MONTHS and size is None:
        return story(asof)
    return grid(asof, size or 144)


DEMO_WORKERS = ('Anna Keller','Luca Meier','Sara Rossi','Jonas Weber','Mira Frei','David Brunner')
STORY_PEOPLE = 1400
STORY_SEED = 2026
# Planted, fictional relationships. They exist so the group analysis has something to find;
# they are not estimates of real outcomes. Listed in the data card shown in the app.
STORY_CARD = (
    'A1 more likely with a language course in the first six months after entry',
    'A1 more likely with more years of schooling and Latin-script literacy',
    'A1 less likely with higher age at entry',
    'A1 less likely for parents of small children (childcare scheduling, recorded in the Situationsanalyse)',
    'Employment more likely after an early course and with more schooling',
    'A household leaves social assistance after a job of 70 %+ lasting 8+ months; one in four returns',
)
ORIGINS = (  # weight, nationality, mother tongue, mean school years, share literate in Latin script
    (26,'Afghanistan','Dari',6,.45), (22,'Eritrea','Tigrinya',7,.55), (18,'Syrien','Arabisch',9,.6),
    (10,'Türkei','Kurdisch',8,.85), (8,'Somalia','Somali',5,.7), (8,'Iran','Farsi',11,.5), (8,'Ukraine','Ukrainisch',12,.3),
)
STATUSES = (('VA',32),('F-FL',8),('B-FL',34),('B-RSFL',4),('B-SL',4),('N (Asylsuchende)',14),('VA+7',2),('B-FL+5',2))
EMPLOYERS = (('Alters- und Pflegeheim Wattenwil','Wattenwil'),('Altersresidenz zur Wiese','Bern'),('Gastro Aare GmbH','Bern'),
             ('Logistik Bümpliz AG','Bern'),('Reinigung Mittelland AG','Ostermundigen'),('Bäckerei Lorraine','Bern'),
             ('Hotel Bärengraben','Bern'),('Bau Wankdorf AG','Bern'),('Spitex Bern Nord','Bern'))
SCHOOLS = ('Heilsarmee LernPunkt','HEKS','ECAP Bern','Volkshochschule Bern')
BERN_PLZ = ('3008','3011','3012','3013','3014','3018','3027')


def add_months(value, count):
    ordinal = value.year*12 + value.month - 1 + count
    year, month = divmod(ordinal, 12)
    day = min(value.day, (date(year+(month==11), (month+1)%12+1, 1) - timedelta(days=1)).day)
    return date(year, month+1, day)


def story(asof, size=STORY_PEOPLE):
    """Fictional caseload. Every draw happens before the report-date filter, so both months share one history."""
    from math import exp
    import random
    rng = random.Random(STORY_SEED)
    report = date.fromisoformat(asof)
    rows = defaultdict(list)

    shown = True

    def add(key, values):
        if shown:
            rows[key].append([values.get(header) for header in SCHEMA[key]['headers']])

    def until(value):
        # Dates after the report date are unknown in that month's export.
        return value if value and value <= report else None

    def chance(logit):
        return rng.random() < 1/(1+exp(-logit))

    def day_in(year):
        start = date(year,1,1)
        span = (date(2026,10,20) if year == 2026 else date(year,12,31)) - start
        return start + timedelta(days=rng.randrange(span.days))

    person_no, household_no = 0, 0
    while person_no < size:
        household_no += 1
        first = household_no in (1, 2)
        kind = 'couple' if household_no == 1 else rng.choices(('single','couple','family','parent'),(40,12,33,15))[0]
        origin = ORIGINS[0] if household_no == 1 else rng.choices(ORIGINS,[o[0] for o in ORIGINS])[0]
        _, nationality, tongue, school_mean, latin_share = origin
        if household_no == 1:
            final = 'VA'
        elif nationality == 'Ukraine':
            final = 'S' if rng.random() < .85 else 'VA'
        else:
            final = rng.choices([s for s,_ in STATUSES],[w for _,w in STATUSES])[0]
        entry = date(2023,10,16) if household_no == 1 else day_in(rng.choices(range(2021,2027),(6,18,24,24,18,10))[0])
        if household_no == 2:
            entry = date(2022,5,9)
        begin = entry + timedelta(days=rng.randrange(0,15))
        application = entry + timedelta(days=rng.randrange(1,5))
        decision = None if final in ('S','N (Asylsuchende)') else add_months(entry, rng.randrange(3,21))
        if household_no == 1:
            decision = date(2024,3,1)
        worker = DEMO_WORKERS[(household_no-1) % len(DEMO_WORKERS)]
        home = f'SYN-H{household_no:05}'
        adults = 1 if kind in ('single','parent') else 2
        children = rng.randrange(1,5) if kind in ('family','parent') else 0
        members = []
        for m in range(adults + children):
            adult = m < adults
            age = 18 + int(rng.betavariate(2,3.5)*40) if adult else rng.randrange(0,18)
            members.append(dict(adult=adult, age=age, female=rng.random() < (.45 if adult else .5),
                                school=max(0,min(16,round(rng.gauss(school_mean,3)))), latin=rng.random() < latin_share,
                                role=('Dossierträger/-in' if m == 0 else 'Ehefrau / -mann' if adult else 'Tochter / Sohn')))
        if household_no == 1:
            members[0].update(age=36, female=True, school=9, latin=True)
        # A household that arrives after the report date is drawn in full but not exported,
        # so both months consume the same random stream.
        shown = begin <= report
        current = 'N (Asylsuchende)' if decision and decision > report else final
        if current in ('VA','F-FL'):
            end = add_months(entry, 84)
        elif current in ('B-FL','B-RSFL','B-SL'):
            end = add_months(application, 60)
        else:
            end = None
        # Household-level employment drives social assistance (goal 3).
        small_children = any(not other['adult'] and other['age'] < 4 for other in members)
        exits, zids = [], []
        for m, member in enumerate(members):
            person_no += 1
            person = f'DEMO-{person_no:05}'
            zid = f'SYN-Z{person_no:05}'
            zids.append(zid)
            ids = {'Klientennummer':person,'Zemis Nummer':zid,'Klient/-in Zemis-Nr.':zid,'Dossier-Nr.':home}
            born = date(entry.year - member['age'], rng.randrange(1,13), rng.randrange(1,29))
            if household_no == 1 and m == 0:
                born = date(1987,4,8)
            school = member['school'] if member['adult'] or member['age'] >= 12 else None
            education_level = ('0 Keine in der Schweiz anerkannte Ausbildung' if (school or 0) < 9 else
                               '130 Obligatorische Schule' if (school or 0) < 12 else
                               '24 Sekundarstufe II: Allgemeinbildung' if (school or 0) < 14 else '32 Hochschule')
            add('clients', ids | {'Unterstützung':None,'Zuständigkeitsbeginn':begin,'Zuständigkeitsende':end,
                'Verfahrensstand':current,'Geschlecht':'Weiblich' if member['female'] else 'Männlich',
                'Nationalität Land':nationality,'Muttersprache':tongue,
                'Zivilstand':'Verheiratet' if kind in ('couple','family') and member['adult'] else 'Ledig',
                'Jahre Arbeitserfahrung vor Einreise':max(0,member['age']-18-(school or 0)//2) if member['adult'] else 0,
                'Höchste abgeschlossene Ausbildung':education_level if member['adult'] else None,
                'Lateinisch alphabetisiert':'Ja' if member['latin'] else 'Nein',
                'Art Analphabetismus':None if member['latin'] else ('Zweitschriftlernende/-r' if (school or 0) >= 6 else 'Primäranalphabet/-in'),
                'Schuljahre vor Einreise':school,'Fallführung':worker,'Geburtsdatum':born})
            add('events', ids | {'Asylgeschäftsart':'Aufenthalt (Einreise)','Ereignisdatum':entry})
            if rng.random() < .012 and not first:
                add('events', ids | {'Asylgeschäftsart':'Aufenthalt (Einreise)','Ereignisdatum':entry - timedelta(days=41)})
            if final != 'S':
                add('events', ids | {'Asylgeschäftsart':'Asylgesuch in CH (Kt normal, Kat. III)','Ereignisdatum':application})
            if decision and decision <= report:
                add('status', ids | {'Verfahrensstand Gültig ab':entry,'Verfahrensstand Gültig bis':decision - timedelta(days=1),
                                     'Verfahrensstand':'N (Asylsuchende)'})
                add('status', ids | {'Verfahrensstand Gültig ab':decision,'Verfahrensstand':final})
            else:
                add('status', ids | {'Verfahrensstand Gültig ab':entry,'Verfahrensstand':current})
            add('membership', ids | {'Dossierperson Von':entry,'Rolle':'Dossiermitglied','Beziehung':member['role']})
            moved = add_months(entry, rng.randrange(5,15))
            postcode = rng.choice(BERN_PLZ)
            add('housing', {'Klientennummer':person,'Unterbringung Von':entry,'Unterbringung Bis':until(moved - timedelta(days=1)),
                            'Unterbringung Art':'Kollektivunterkunft','PLZ':'3008','Ort':'Bern'})
            if moved <= report:
                add('housing', {'Klientennummer':person,'Unterbringung Von':moved,'Unterbringung Art':'Indiv. Wohnung',
                                'PLZ':postcode,'Ort':'Bern'})
            age_at_entry = member['age']
            # Language course timing: early (≤ 6 months), late, or none.
            draw = rng.random()
            lag = rng.randrange(1,7) if draw < .5 else rng.randrange(7,21) if draw < .8 else None
            early, late = lag is not None and lag <= 6, lag is not None and lag > 6
            school_name, hours = rng.choice(SCHOOLS), rng.choice((8,10,12,16))
            if household_no == 1 and m == 0:
                lag, early, late = 23, False, True
            if age_at_entry >= 14 and lag is not None:
                course = add_months(entry, lag)
                if course <= report:
                    add('education', ids | {'Start':course,'Abschluss':until(add_months(course,5)),
                        'Institution Name':school_name,'Art':'Förderangebot Sprache',
                        'Bezeichnung':'A1 Deutsch halbintensiv' if member['latin'] else 'Alphabetisierung 1 halbintensiv',
                        'Stunden pro Woche':hours})
            # Goal 1: A1 evidence.
            logit = (-.1 + 1.7*early + .6*late + .25*((school or 6)-8) - .06*(age_at_entry-30) + .5*member['latin']
                     - 1.1*(member['adult'] and small_children))
            attains = chance(logit)
            months = max(4, rng.uniform(6,48) - 9*early)
            proof_kind = rng.random()
            remark = rng.choice(('fide','telc','telc Deutsch A1','fide A1 mündlich/schriftlich'))
            level = rng.choices(('A1','A2','B1'),(70,25,5))[0]
            french = rng.random() < .05
            official_draw = rng.random()
            official_shift = rng.randrange(20,60)
            if rng.random() < .3 and add_months(entry,2) <= report:
                add('language', ids | {'Sprache':'Deutsch','Sprachniveau':'A0','Art':'Weiteres','Bemerkungen':'Einstufung',
                                       'Datum Erreichung':add_months(entry,2)})
            if household_no == 1 and m == 0:
                attains, proof_date, proof_kind, remark, level, french, official_draw = True, date(2026,10,12), .5, 'fide', 'A1', False, .99
            elif age_at_entry < 16 and age_at_entry >= 10:
                proof_date = add_months(entry, rng.randrange(12,36))
                attains, proof_kind = rng.random() < .8, 'school'
            else:
                proof_date = entry + timedelta(days=int(months*30.4))
            if attains and age_at_entry >= 10 and proof_date <= report:
                if proof_kind == 'school':
                    kind_row = {'Art':'Beendigung obligatorische Schulzeit','Bemerkungen':'Volksschule Bern'}
                elif proof_kind < .07:
                    kind_row = {'Art':'Zertifizierung','Bemerkungen':'Zertifikat eingereicht'}
                elif proof_kind < .9:
                    kind_row = {'Art':'Zertifizierung','Bemerkungen':remark}
                else:
                    kind_row = {'Art':'Beendigung Ausbildung','Bemerkungen':'Abschluss Ausbildung'}
                add('language', ids | kind_row | {'Sprache':'Französisch' if french else 'Deutsch','Sprachniveau':level,
                                                  'Datum Erreichung':proof_date})
                recorded = proof_date if official_draw < .8 else proof_date + timedelta(days=official_shift) if official_draw < .86 else None
                if recorded and recorded <= report and not french:
                    add('official', {'Klient/-in Zemis-Nr.':zid,'Art':'Sprachniveau A1','Erreicht am':recorded,
                                     'Partner':'Bern Stadt und Umgebung','Jahr Grundgesamtheit':entry.year,'Ziel mit Status S erreicht':'Nein'})
            # Goal 2: employment or upper-secondary / tertiary education.
            working_age = member['adult'] and age_at_entry <= 58
            job = working_age and not first and chance(-.9 + .7*early + .09*((school or 6)-8) - .6*(age_at_entry > 45))
            start = add_months(entry, rng.randrange(8,40))
            percent = rng.choices((40,50,60,70,80,100),(10,12,12,10,26,30))[0]
            length = None if rng.random() < .35 else rng.randrange(2,30)
            second_market = rng.random() < .08
            employer, town = rng.choice(EMPLOYERS)
            again = rng.random() < .25
            gap = rng.randrange(1,4)
            zemis_draw = rng.random()
            record_draw = rng.random()
            if job and start <= report:
                finish = add_months(start, length) - timedelta(days=1) if length else None
                remark = 'Beschäftigungsprogramm (2. Arbeitsmarkt)' if second_market else None
                add('work', ids | {'Von':start,'Bis':until(finish),'Arbeitgeber Name':employer,'Arbeitgeber Ort':town,
                    'Pensum %':percent,'Erwerbsstatus':'unselbstständig','Monatseinkommen brutto CHF':percent*45,
                    'Unregelmässiges Einkommen':'Nein','Abtretung Sozialdienst':'Nein','Bemerkungen':remark})
                if zemis_draw < .94:
                    add('zemis', ids | {'Arbeitsbeginn':start,'Verpflichtet bis':until(finish),
                                        'Betrieb':'Adecco' if zemis_draw > .89 else employer})
                if finish and again and add_months(finish, gap) <= report:
                    restart = add_months(finish, gap)
                    add('work', ids | {'Von':restart,'Arbeitgeber Name':employer,'Arbeitgeber Ort':town,'Pensum %':percent,
                        'Erwerbsstatus':'unselbstständig','Monatseinkommen brutto CHF':percent*45,
                        'Unregelmässiges Einkommen':'Nein','Abtretung Sozialdienst':'Nein'})
                if percent >= 70 and not second_market and (length is None or length >= 8):
                    exits.append(add_months(start, 2))
                recorded = add_months(start, 6)
                if percent >= 60 and not second_market and (length is None or length >= 6) and record_draw < .7 and recorded <= report:
                    add('official', {'Klient/-in Zemis-Nr.':zid,'Art':'Aufnahme Ausbildung / Erwerbstätigkeit','Erreicht am':recorded,
                                     'Partner':'Bern Stadt und Umgebung','Jahr Grundgesamtheit':entry.year,'Ziel mit Status S erreicht':'Nein'})
            elif working_age and zemis_draw < .04 and start <= report:
                add('zemis', ids | {'Arbeitsbeginn':start,'Betrieb':employer})
            young = 15 <= age_at_entry <= 25
            study = young and rng.random() < .18
            study_start = add_months(entry, rng.randrange(12,36))
            tertiary = rng.random() < .25
            if study and study_start <= report:
                add('education', ids | {'Start':study_start,'Institution Name':'Gymnasium Neufeld' if tertiary else 'Berufsfachschule Bern',
                    'Art':'Tertiär' if tertiary else 'Sek II',
                    'Bezeichnung':'Bachelorstudium Pflege' if tertiary else 'EFZ Fachfrau/Fachmann Gesundheit','Stunden pro Woche':38})
                if record_draw < .7 and not job:
                    add('official', {'Klient/-in Zemis-Nr.':zid,'Art':'Aufnahme Ausbildung / Erwerbstätigkeit','Erreicht am':study_start,
                                     'Partner':'Bern Stadt und Umgebung','Jahr Grundgesamtheit':entry.year,'Ziel mit Status S erreicht':'Nein'})
        # Goal 3: household assistance periods.
        relapse = rng.random() < .25
        relapse_after = rng.randrange(4,11)
        relapse_long = rng.randrange(3,12)
        household_record = rng.random()
        stop = min(exits) if exits else None
        support_end = until(stop - timedelta(days=1)) if stop else None
        add('support', {'Dossier-Nr.':home,'Unterstützung':'Sozialhilfe','Finanzielle Unterstützung Gültig von':begin,
                        'Finanzielle Unterstützung Gültig bis':support_end,
                        'Hauptgrund Beendigung Unterstützung':'Aufnahme einer Erwerbstätigkeit' if support_end else None})
        independent = add_months(stop, 12) if stop else None
        if stop and not relapse and household_record < .65 and independent <= report:
            for zid in zids:
                add('official', {'Klient/-in Zemis-Nr.':zid,'Art':'Finanzielle Unabhängigkeit','Erreicht am':independent,
                                 'Partner':'Bern Stadt und Umgebung','Jahr Grundgesamtheit':entry.year,'Ziel mit Status S erreicht':'Nein'})
        if stop and relapse and add_months(stop, relapse_after) <= report:
            back = add_months(stop, relapse_after)
            add('support', {'Dossier-Nr.':home,'Unterstützung':'Sozialhilfe','Finanzielle Unterstützung Gültig von':back,
                            'Finanzielle Unterstützung Gültig bis':until(add_months(back, relapse_long))})
    return {key:xlsx.write({key:[spec['headers'],*rows[key]]}) for key,spec in SCHEMA.items()}


def grid(asof, size):
    rows = defaultdict(list)
    phase4 = asof==PHASE4_MONTH
    phase5 = asof==PHASE5_MONTH
    if phase5:
        size = max(480,size)
    def add(key, values):
        rows[key].append([values.get(header) for header in SCHEMA[key]['headers']])
    for i in range(size):
        person = f'DEMO-{i+1:05}'
        z = f'SYN-Z{i+1:05}'
        household = f'SYN-H{i//2+1:05}'
        ids = {'Klientennummer':person,'Zemis Nummer':z,'Klient/-in Zemis-Nr.':z,'Dossier-Nr.':household}
        entry = date(2022+i%4, 10 if i == 1 else 1+i%12, 1+i%24)
        if phase5:
            entry = date(2022+(i//6)%2,1+i%6,1+i%24)
        elif i == 0:
            entry = date(2023,10,16)
        status = ('VA','B-FL','F-FL','B-RSFL','S','N (Asylsuchende)')[i%6]
        end = date(2028+(i//2)%2,6,30)
        worker = ('A','B','C')[(i//2)%3]
        add('clients', ids | {'Geburtsdatum':date(1977+i%36,4,8),'Zuständigkeitsbeginn':entry,'Zuständigkeitsende':end,
                             'Datum Übergang Gemeindezuständigkeit':None,'Fallführung':worker,'Verfahrensstand':status,
                             'Schuljahre vor Einreise':4+i%12,'Muttersprache':('Arabisch','Tigrinya','Dari')[i%3]})
        add('events',ids | {'Asylgeschäftsart':'Aufenthalt (Einreise)','Ereignisdatum':entry})
        add('events',ids | {'Asylgeschäftsart':'Asylgesuch in CH (Kt normal, Kat. III)','Ereignisdatum':entry + timedelta(days=2)})
        add('status',ids | {'Verfahrensstand Gültig ab':entry,'Verfahrensstand':status})
        member_start = date(2026,6,1) if phase4 and i==1 else entry
        add('membership',ids | {'Dossierperson Von':member_start,'Rolle':'Familienmitglied'})
        add('housing',ids | {'Unterbringung Von':entry,'Unterbringung Art':'Wohnung','PLZ':'3000','Ort':'Bern'})
        if i%4 != 3:
            proof = entry+timedelta(days=(150 if (i//6)%10<5 else 1250)) if phase5 else (date(2026,10,12) if i == 0 else entry + timedelta(days=200+i*11))
            if str(proof) <= asof:
                add('language', ids | {'Sprache':'Deutsch','Sprachniveau':'A2' if i%5 else 'A1',
                     'Art':'Zertifizierung','Bemerkungen':'fide','Datum Erreichung':proof})
                if i%7:
                    add('official',ids | {'Art':'Sprachniveau A1','Erreicht am':proof,'Jahr Grundgesamtheit':entry.year,'Ziel mit Status S erreicht':'Nein'})
        if phase4 and i==1:
            for begin, finish in ((date(2026,1,1),date(2026,3,31)),(date(2026,4,2),None)):
                add('work',ids | {'Von':begin,'Bis':finish,'Pensum %':80,'Erwerbsstatus':'unselbstständig',
                                  'Bemerkungen':'Demo: 1. Arbeitsmarkt'})
        elif i%3:
            job = max(entry,date(2025,3+i%8,1))
            add('work',ids | {'Von':job,'Pensum %':80 if i%5 else 50,'Arbeitgeber Name':'Demo Betrieb','Erwerbsstatus':'unselbstständig','Bemerkungen':'Demo: 1. Arbeitsmarkt'})
        if i%3 or i%11 == 0:
            add('zemis',ids | {'Arbeitsbeginn':max(entry,date(2025,3+i%8,1)),'Betrieb':'Demo Betrieb'})
        if i%3 == 0:
            add('education',ids | {'Start':max(entry,date(2025,8,1)),'Art':'Sek II' if i%4==0 else 'Förderangebot Sprache',
                                   'Institution Name':'Demo Lernzentrum','Stunden pro Woche':8})
        if i%2 == 0:
            add('support',ids | {'Unterstützung':None if phase4 and i==2 else 'Sozialhilfe','Finanzielle Unterstützung Gültig von':date(2022,1,1),
                'Finanzielle Unterstützung Gültig bis':date(2025,8,15) if i%4==0 else None})
    return {key:xlsx.write({key:[spec['headers'],*rows[key]]}) for key,spec in SCHEMA.items()}


def story_intake(cases):
    """Fictional, already human-confirmed Situationsanalyse categories for the demo months.

    Derived only from facts the exports also show (household children, schooling, courses);
    every fourth person has no reviewed report, so missing intake stays visible."""
    young = {c['home'] for c in cases if c['age'] is not None and c['age'] < 8}
    labels = {}
    for case in cases:
        number = int(case['id'].removeprefix('DEMO-')) if case['id'].startswith('DEMO-') else 0
        if number % 4 == 0 or case['age'] is None or case['age'] < 16:
            continue
        if case['home'] in young and case['age'] >= 20:
            labels[case['id']] = 'scheduling'
        elif isinstance(case['school_years'],(int,float)) and case['school_years'] < 6:
            labels[case['id']] = 'schooling'
        elif case['tables']['education']:
            labels[case['id']] = 'course'
        else:
            labels[case['id']] = 'housing'
    return labels


def phase5_categories(cases):
    """Fictional pre-reviewed records for the dedicated synthetic analysis fixture."""
    categories = ('schooling','course','scheduling','housing')
    sample = ((case['id'],int(case['id'].removeprefix('DEMO-'))-1) for case in cases)
    return {identifier:categories[(n//13)%len(categories)] for identifier,n in sample if n%7}


class ImportFailure(Exception):
    def __init__(self, errors):
        self.errors = errors


def connect(path,initialize=True):
    db = sqlite3.connect(path,timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    if not initialize:
        return db
    db.executescript("""
      CREATE TABLE IF NOT EXISTS snapshots(
        id INTEGER PRIMARY KEY, asof TEXT NOT NULL, source TEXT NOT NULL, digest TEXT UNIQUE,
        created TEXT NOT NULL, inspected TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS source_rows(
        snapshot INTEGER REFERENCES snapshots(id) ON DELETE CASCADE,
        dataset TEXT, line INTEGER, content TEXT, PRIMARY KEY(snapshot,dataset,line));
      CREATE TABLE IF NOT EXISTS accounts(username TEXT PRIMARY KEY, password TEXT, role TEXT, assignment TEXT);
      CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, username TEXT REFERENCES accounts(username),
        csrf TEXT, expires INTEGER, selected INTEGER REFERENCES snapshots(id) ON DELETE SET NULL);
      CREATE TABLE IF NOT EXISTS source_manifest(
        snapshot INTEGER REFERENCES snapshots(id) ON DELETE CASCADE,
        dataset TEXT, sha256 TEXT NOT NULL, PRIMARY KEY(snapshot,dataset));
      CREATE TABLE IF NOT EXISTS import_diagnostics(
        session TEXT PRIMARY KEY REFERENCES sessions(token) ON DELETE CASCADE,
        report_date TEXT, outcome TEXT NOT NULL, issues TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS audit(at TEXT, action TEXT, outcome TEXT);
      CREATE TABLE IF NOT EXISTS forecast_input(
        username TEXT PRIMARY KEY REFERENCES accounts(username) ON DELETE CASCADE, series TEXT);
      CREATE TABLE IF NOT EXISTS demo_roles(
        session TEXT PRIMARY KEY REFERENCES sessions(token) ON DELETE CASCADE,
        role TEXT NOT NULL CHECK(role IN ('worker','manager','importer')));
      CREATE TABLE IF NOT EXISTS intake_demo(
        session TEXT REFERENCES sessions(token) ON DELETE CASCADE,
        snapshot INTEGER REFERENCES snapshots(id) ON DELETE CASCADE,
        category TEXT NOT NULL, PRIMARY KEY(session,snapshot));
      CREATE TABLE IF NOT EXISTS intake(snapshot INTEGER REFERENCES snapshots(id) ON DELETE CASCADE,
        person TEXT, category TEXT, PRIMARY KEY(snapshot,person));
    """)
    return db


def load_files(db, files, asof, source):
    report = date.fromisoformat(asof)
    recognized = {}
    issues = []
    hashed = sha256(f'{report}:{source}'.encode())
    headers = {frozenset(item['headers']):key for key,item in SCHEMA.items()}
    for n, blob in enumerate(files,1):
        try:
            stream = xlsx.read(blob)
            _, header, mac = next(stream)
            header = tuple(norm(value) for value in header)
            key = headers.get(frozenset(header)) if len(set(header)) == len(header) else None
            if key is None or key in recognized:
                raise ValueError('unknown_or_duplicate_contract')
            recognized[key] = (blob, header, mac)
        except (ValueError,TypeError,OverflowError,BadZipFile,KeyError,StopIteration,ParseError,IndexError):
            issues.append((f'file {n}',1,'unrecognized_or_invalid_workbook'))
        finally:
            stream.close()
    issues.extend((key,1,'missing_source') for key in SCHEMA.keys()-recognized.keys())
    if issues:
        raise ImportFailure(issues)
    for key,(blob,_,_) in sorted(recognized.items()):
        hashed.update(key.encode())
        hashed.update(sha256(blob).digest())
    digest = hashed.hexdigest()
    count = {}
    clients, zemis, homes = {}, {}, set()
    current_status = defaultdict(set)
    with db:
        cursor = db.execute('INSERT OR IGNORE INTO snapshots(asof,source,digest,created,inspected) VALUES(?,?,?,?,?)',
                            (asof,source,digest,datetime.now(timezone.utc).isoformat(),'{}'))
        if cursor.rowcount == 0:
            snapshot = db.execute('SELECT id FROM snapshots WHERE digest=?',(digest,)).fetchone()[0]
        else:
            snapshot = cursor.lastrowid
        db.executemany('INSERT OR IGNORE INTO source_manifest VALUES(?,?,?)',
                       ((snapshot,key,sha256(blob).hexdigest()) for key,(blob,_,_) in recognized.items()))
        if cursor.rowcount == 0:
            return snapshot, True
        for key in ['clients',*(k for k in SCHEMA if k!='clients')]:
            blob, header, mac = recognized[key]
            seen = set()
            batch = []
            count[key] = 0
            for line, cells, _ in read_data_rows(blob,key):
                if len(issues) >= 100:
                    break
                if not any(x not in (None,'') for x in cells):
                    continue
                if any(value not in (None,'') for value in cells[len(header):]):
                    issues.append((key,line,'unexpected_column'))
                    continue
                row = dict(zip(header,(norm(value) for value in cells),strict=False))
                try:
                    for k in IDS:
                        # Real exports store Klientennummer / ZEMIS numbers as whole-number cells.
                        if isinstance(row.get(k),float) and row[k].is_integer() and 0 < row[k] < 1e15:
                            row[k] = str(int(row[k]))
                    if any(row.get(k) is not None and not isinstance(row[k],str) for k in IDS):
                        raise ValueError('numeric_identifier')
                    for k in DATES[key]:
                        value = xlsx.excel_date(row.get(k),mac)
                        row[k] = value.isoformat() if value else None
                    if key in PAIR:
                        start,end = (row.get(k) for k in PAIR[key])
                        if start and end and start>end:
                            raise ValueError('date_range')
                    canonical = json.dumps(row,ensure_ascii=False,sort_keys=True)
                    if canonical in seen:
                        raise ValueError('duplicate_row')
                    seen.add(canonical)
                    person = row.get('Klientennummer')
                    zid = row.get('Zemis Nummer') or row.get('Klient/-in Zemis-Nr.')
                    home = row.get('Dossier-Nr.')
                    if key == 'clients':
                        if not person or not zid or not home or person in clients or zid in zemis:
                            raise ValueError('invalid_or_conflicting_client_key')
                        clients[person] = zid
                        zemis[zid] = person
                        homes.add(home)
                    else:
                        if key in ('support','membership') and home not in homes:
                            raise ValueError('unresolved_household')
                        if key != 'support' and ((not person and not zid) or (person and person not in clients)
                             or (zid and zid not in zemis) or (person and zid and clients[person] != zid)):
                            raise ValueError('unresolved_or_conflicting_person')
                        if key=='status' and start and start<=asof and (not end or end>=asof):
                            identity = person or zemis[zid]
                            current_status[identity].add(row.get('Verfahrensstand'))
                            if len(current_status[identity])>1:
                                raise ValueError('conflicting_current_status')
                    row['_person'] = person or zemis.get(zid)
                    row['_line'] = line
                    batch.append((snapshot,key,line,json.dumps(row,ensure_ascii=False)))
                    count[key]+=1
                    if len(batch)==500:
                        db.executemany('INSERT INTO source_rows VALUES(?,?,?,?)',batch)
                        batch.clear()
                except (ValueError,TypeError,OverflowError) as exc:
                    code = str(exc)
                    issues.append((key,line,code if code.replace('_','').isalpha() and ' ' not in code else 'invalid_value'))
            db.executemany('INSERT INTO source_rows VALUES(?,?,?,?)',batch)
        if not clients:
            issues.append(('clients',1,'empty_clients'))
        if issues:
            raise ImportFailure(issues)
        db.execute('UPDATE snapshots SET inspected=? WHERE id=?',(json.dumps(count),snapshot))
        db.execute('INSERT INTO audit VALUES(datetime("now"),?,?)',('snapshot_import','accepted'))
    return snapshot, False



def read_data_rows(blob,key):
    line = 1
    try:
        with closing(xlsx.read(blob)) as stream:
            next(stream)
            for line, cells, mac in stream:
                yield line, cells, mac
    except (ValueError,TypeError,OverflowError,BadZipFile,KeyError,StopIteration,ParseError,IndexError) as exc:
        raise ImportFailure([(key,line+1,'invalid_worksheet_data')]) from exc


def snapshot_metadata(db, id=None, synthetic_only=False):
    return db.execute(
        'SELECT * FROM snapshots WHERE (? IS NULL OR id=?) AND (?=0 OR source="synthetic") '
        'ORDER BY asof DESC,id DESC LIMIT 1',(id,id,synthetic_only)).fetchone()



def get_snapshot(db, id=None):
    row = snapshot_metadata(db,id)
    if not row:
        return None, {}
    data = defaultdict(list)
    for entry in db.execute('SELECT dataset,content FROM source_rows WHERE snapshot=? ORDER BY dataset,line',(row['id'],)):
        data[entry['dataset']].append(json.loads(entry['content']))
    return row,data


def backup(db, destination):
    """Create a consistent private backup without replacing an existing file."""
    import os
    from tempfile import mkstemp
    destination = Path(destination)
    parent = destination.parent
    fd, temporary = mkstemp(prefix='.cockpit-backup-',dir=parent)
    os.close(fd)
    try:
        with closing(sqlite3.connect(temporary)) as copy:
            db.backup(copy)
            if copy.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise OSError('backup integrity check failed')
        os.link(temporary,destination)
    finally:
        os.unlink(temporary)


def revoke_sessions(db):
    with db:
        return db.execute('DELETE FROM sessions').rowcount
