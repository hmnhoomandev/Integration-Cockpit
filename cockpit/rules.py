"""Versioned prototype rules. All cutoffs are calendar dates, inclusive."""
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date, timedelta

VERSION = '2026.11-demo.1'
ELIGIBLE = {'VA','F-FL','B-FL','B-RSFL','B-SL'}
OUT = {'N','N (Asylsuchende)','S'}
LEVELS = {'A1','A2','B1','B2','C1','C2'}
MIN_GROUP = 8
DAY = timedelta(days=1)


def as_date(value):
    return date.fromisoformat(value) if value else None


def months(value, count):
    ordinal = value.year*12+value.month-1+count
    year, month = divmod(ordinal,12)
    return date(year,month+1,min(value.day,monthrange(year,month+1)[1]))


def result(state, reason, deadline=None, achieved=None, evidence=(), earliest=None):
    return dict(state=state,reason=reason,deadline=deadline,achieved=achieved,
        evidence=list(evidence),earliest=earliest)


def judgement(asof, due, attained, evidence, reason, earliest=None):
    if attained:
        return result('late' if attained>due else 'achieved',reason,due,attained,evidence,earliest)
    return result('overdue' if asof>=due else 'risk' if (due-asof).days<=90 else 'ontrack',
                  reason,due,None,evidence,earliest)


def intervals(rows, start_col, end_col, start, end):
    pairs = []
    for row in rows:
        a = as_date(row.get(start_col))
        b = as_date(row.get(end_col)) or end
        if a and a<=end and b>=start:
            pairs.append((max(start,a),min(end,b),row['_line']))
    merged = []
    for a,b,line in sorted(pairs):
        if merged and a<=merged[-1][1]+DAY:
            c,d,lines = merged[-1]
            merged[-1] = c,max(b,d),lines+[line]
        else:
            merged.append((a,b,[line]))
    return merged


def goal1(person, entry, asof, tables):
    deadline = months(entry,36)
    qualifying = []
    uncertain = False
    for row in tables['language']:
        if row.get('Sprache')!='Deutsch' or row.get('Sprachniveau') not in LEVELS:
            continue
        kind = row.get('Art')
        note = (row.get('Bemerkungen') or '').casefold()
        if kind=='Zertifizierung' and not any(word in note.split() for word in ('telc','fide')):
            uncertain = True
            continue
        if kind not in ('Zertifizierung','Muttersprache','Beendigung Ausbildung','Beendigung obligatorische Schulzeit'):
            continue
        d = as_date(row.get('Datum Erreichung'))
        if d is None:
            uncertain = True
        elif d<=asof:
            qualifying.append((d,row['_line']))
    official = sorted((as_date(r['Erreicht am']),r['_line']) for r in tables['official']
                      if r.get('Art')=='Sprachniveau A1' and r.get('Erreicht am') and r['Erreicht am']<=asof.isoformat())
    evidence = [('official',line) for _,line in official]
    if qualifying:
        d,line = min(qualifying)
        return judgement(asof,deadline,d,evidence+[('language',line)],
                         'proof' if official and official[0][0]==d else 'proof_difference')
    if uncertain or official:
        return result('review','verify_proof',deadline,evidence=evidence)
    return judgement(asof,deadline,None,[],'missing_proof')


def goal2(tables, asof, start, end):
    if not end:
        return result('review','missing_end')
    cutoff = min(end,asof)
    jobs = [r for r in tables['work'] if r.get('Erwerbsstatus')=='1. Arbeitsmarkt'
            and isinstance(r.get('Pensum %'),(int,float)) and r['Pensum %']>=60]
    spans = intervals(jobs,'Von','Bis',start,cutoff)
    paths = []
    earliest = None
    for a,b,lines in spans:
        target = months(a,6)
        if target<=b:
            paths.append((target,'employment',[('work',line) for line in lines]))
        elif b==asof and target<=end:
            earliest = target
    for row in tables['education']:
        start_education = as_date(row.get('Start'))
        if row.get('Art') in ('Sek II','Tertiär') and start_education and start<=start_education<=cutoff:
            paths.append((start_education,'education',[('education',row['_line'])]))
    if paths:
        d,reason,ev = min(paths)
        return judgement(asof,end,d,ev,reason)
    return judgement(asof,end,None,[],'check_continuity',earliest)


def goal3(household, members, assistance, end, asof, synthetic):
    if not synthetic or not end or not members or any(not r.get('Dossierperson Von') for r in members):
        return result('review','coverage_unknown',end)
    cut = min(end,asof)
    first = min(as_date(r['Dossierperson Von']) for r in members)
    support = intervals(assistance,'Finanzielle Unterstützung Gültig von','Finanzielle Unterstützung Gültig bis',first,cut)
    ev = [('membership',r['_line']) for r in members]
    cursor = first
    for a,b,lines in support:
        ev.extend(('support',line) for line in lines)
        if months(cursor,12)<a:
            return judgement(asof,end,months(cursor,12),ev,'support_free')
        cursor = max(cursor,b+DAY)
    candidate = months(cursor,12)
    return judgement(asof,end,candidate if candidate<=cut else None,ev,'support_free' if candidate<=cut else 'support_check',
                     candidate if cut<candidate<=end else None)


def evaluate(snapshot, rows):
    now = date.fromisoformat(snapshot['asof'])
    indexes = defaultdict(lambda:defaultdict(list))
    household = defaultdict(lambda:defaultdict(list))
    ends = defaultdict(set)
    for table, entries in rows.items():
        for row in entries:
            if row.get('_person'):
                indexes[row['_person']][table].append(row)
            if row.get('Dossier-Nr.'):
                household[row['Dossier-Nr.']][table].append(row)
    for person in rows.get('clients',[]):
        ends[person['Dossier-Nr.']].add(person.get('Zuständigkeitsende'))
    houses = {}
    cases = []
    for person in rows.get('clients',[]):
        pid = person['_person']
        tables = indexes[pid]
        home = person['Dossier-Nr.']
        start = as_date(person.get('Zuständigkeitsbeginn'))
        end = as_date(person.get('Zuständigkeitsende'))
        born = as_date(person.get('Geburtsdatum'))
        status = person.get('Verfahrensstand')
        active = {r.get('Verfahrensstand') for r in tables['status'] if r.get('Verfahrensstand Gültig ab')
                and r['Verfahrensstand Gültig ab']<=snapshot['asof']<= (r.get('Verfahrensstand Gültig bis') or '9999')}
        entries = {as_date(r.get('Ereignisdatum')) for r in tables['events'] if r.get('Asylgeschäftsart')=='Aufenthalt (Einreise)'}
        entry = next(iter(entries)) if len(entries)==1 else None
        age = now.year-born.year-((now.month,now.day)<(born.month,born.day)) if born else None
        if status in OUT or (age is not None and age<16) or (start and start>now) or (end and end<now):
            language=employment=result('na','outside_scope')
        elif status not in ELIGIBLE or not born or not start or (active and active!={status}):
            language=employment=result('review','scope_unknown')
        else:
            language = goal1(person,entry,now,tables) if entry and entry<=now else result('review','entry_unknown')
            employment = goal2(tables,now,start,end)
        if home not in houses:
            family = household[home]
            cutoff = as_date(next(iter(ends[home]))) if len(ends[home])==1 else None
            houses[home] = goal3(home,family['membership'],family['support'],cutoff,now,snapshot['source']=='synthetic')
        financial = houses[home] if language['state']!='na' else result('na','outside_scope')
        gaps = []
        for z in tables['zemis']:
            a = z.get('Arbeitsbeginn')
            b = z.get('Verpflichtet bis') or '9999'
            if a and a<=snapshot['asof'] and not any(w.get('Von') and w['Von']<=b and (w.get('Bis') or '9999')>=a for w in tables['work']):
                gaps.append(z['_line'])
        cases.append(dict(id=pid,worker=person.get('Fallführung') or '–',home=home,entry=entry,age=age,
            status=status,goals=(language,employment,financial),tables=tables,gaps=gaps,end=end))
    return cases


def group_metrics(cases):
    groups = defaultdict(list)
    for case in cases:
        goal = case['goals'][0]
        if case['entry'] and goal['state'] not in ('na','review'):
            groups[case['entry'].year].append(goal)
    # Display only a fixed partition, and suppress both numerator and denominator together.
    return [(year,len(rows),sum(r['state']=='achieved' for r in rows)) if len(rows)>=MIN_GROUP else (year,None,None)
            for year,rows in sorted(groups.items())]


def counts(cases, goal):
    if goal==2:
        cases = {c['home']:c for c in cases if c['goals'][goal]['state']!='na'}.values()
    return Counter(case['goals'][goal]['state'] for case in cases)
