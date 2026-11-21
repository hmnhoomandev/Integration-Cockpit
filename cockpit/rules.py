"""Versioned prototype rules. All cutoffs are calendar dates, inclusive."""
from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date, timedelta
from math import sqrt
from pathlib import Path
from hashlib import sha256
import json
import os
import re

def load_a1_policy(path):
    policy = json.loads(Path(path).read_text())
    if (set(policy) != {'language','minimum_age','age_reference','eligible_statuses','excluded_statuses','accepted_proof_types'}
        or policy['language'] not in ('Deutsch','Französisch')
        or type(policy['minimum_age']) is not int or not 0 <= policy['minimum_age'] <= 100
        or policy['age_reference'] not in ('report_date','entry_date')):
        raise ValueError('Invalid A1 demo policy')
    for key in ('eligible_statuses','excluded_statuses','accepted_proof_types'):
        if not isinstance(policy[key],list) or not policy[key] or any(not isinstance(item,str) or not item.strip() for item in policy[key]):
            raise ValueError(f'Invalid A1 policy list: {key}')
    if set(policy['eligible_statuses']) & set(policy['excluded_statuses']):
        raise ValueError('A1 status lists overlap')
    return policy


A1_POLICY = load_a1_policy(os.getenv('COCKPIT_A1_POLICY') or Path(__file__).with_name('a1-policy.json'))
VERSION = '2026.11-demo.2+'+sha256(json.dumps(A1_POLICY,sort_keys=True).encode()).hexdigest()[:10]
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
        if row.get('Sprache')!=A1_POLICY['language'] or row.get('Sprachniveau') not in LEVELS:
            continue
        kind = row.get('Art')
        note = (row.get('Bemerkungen') or '').casefold()
        if kind not in A1_POLICY['accepted_proof_types']:
            continue
        d = as_date(row.get('Datum Erreichung'))
        if d and d>asof:
            continue
        if kind=='Zertifizierung' and not re.search(r'\b(?:telc|fide)\b',note):
            uncertain = True
            continue
        if d is None:
            uncertain = True
        elif d<=asof:
            qualifying.append((d,row['_line']))
    official = [(as_date(r.get('Erreicht am')),r['_line']) for r in tables['official']
                if r.get('Art')=='Sprachniveau A1' and (not r.get('Erreicht am') or r['Erreicht am']<=asof.isoformat())]
    dates = sorted({d for d,_ in official if d})
    undated = any(d is None for d,_ in official)
    evidence = [('official',line) for _,line in official]
    if qualifying:
        d,line = min(qualifying)
        same = dates==[d] and not undated
        answer = judgement(asof,deadline,d,evidence+[('language',line)],'proof' if same else 'proof_difference')
    elif uncertain or official:
        answer = result('review','verify_proof',deadline,evidence=evidence)
    else:
        answer = judgement(asof,deadline,None,[],'missing_proof')
        if asof==deadline:
            answer['state'] = 'risk'
    return answer | {'scope':'scope_in','due':asof>=deadline,'official_dates':dates,'official_undated':undated,
                     'proof_uncertain':uncertain}


def goal2(tables, asof, start, end, synthetic=False):
    if not end:
        return result('review','missing_end')
    cutoff = min(end,asof)
    potential_jobs = [r for r in tables['work'] if isinstance(r.get('Pensum %'),(int,float))
                      and r['Pensum %']>=60 and r.get('Von') and r['Von']<=cutoff.isoformat()
                      and (not r.get('Bis') or r['Bis']>=start.isoformat())]
    jobs = [r for r in potential_jobs if r.get('Erwerbsstatus')=='1. Arbeitsmarkt'
            or (synthetic and r.get('Bemerkungen')=='Demo: 1. Arbeitsmarkt')]
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
    if len(jobs)<len(potential_jobs):
        return result('review','market_unknown',end,evidence=[('work',r['_line']) for r in potential_jobs if r not in jobs])
    return judgement(asof,end,None,[],'check_continuity',earliest)


def goal3(household, members, assistance, end, asof, synthetic):
    if not synthetic or not end or not members or any(not r.get('Dossierperson Von') for r in members):
        return result('review','coverage_unknown',end)
    cut = min(end,asof)
    first = min(as_date(r['Dossierperson Von']) for r in members)
    support_types = {'Sozialhilfe','Nothilfe','Keine Unterstützung'}
    if any(r.get('Unterstützung') not in support_types for r in assistance):
        return result('review','coverage_unknown',end)
    support = intervals([r for r in assistance if r['Unterstützung']!='Keine Unterstützung'],
                        'Finanzielle Unterstützung Gültig von','Finanzielle Unterstützung Gültig bis',first,cut)
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


def age_on(born, when):
    if not born or not when or born>when:
        return None
    return when.year-born.year-((when.month,when.day)<(born.month,born.day))


def a1_scope(status,born,start,end,active,entry,now):
    reference = entry if A1_POLICY['age_reference']=='entry_date' else now
    age = age_on(born,reference)
    if status in A1_POLICY['excluded_statuses'] or (age is not None and age<A1_POLICY['minimum_age']) or (start and start>now) or (end and end<now):
        return 'scope_out'
    if status not in A1_POLICY['eligible_statuses'] or age is None or not start or (active and active!={status}):
        return 'scope_review'
    return 'scope_in'


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
        age = age_on(born,now)
        if status in OUT or (age is not None and age<16) or (start and start>now) or (end and end<now):
            employment=result('na','outside_scope')
        elif status not in ELIGIBLE or not born or not start or (active and active!={status}):
            employment=result('review','scope_unknown')
        else:
            employment = goal2(tables,now,start,end,snapshot['source']=='synthetic')
        scope = a1_scope(status,born,start,end,active,entry,now)
        if scope=='scope_out':
            language = result('na','outside_scope') | {'scope':scope}
        elif scope=='scope_review':
            language = result('review','scope_unknown') | {'scope':scope}
        elif not entry or entry>now:
            language = result('review','entry_unknown') | {'scope':scope}
        else:
            language = goal1(person,entry,now,tables)
        if home not in houses:
            family = household[home]
            cutoff = as_date(next(iter(ends[home]))) if len(ends[home])==1 else None
            houses[home] = goal3(home,family['membership'],family['support'],cutoff,now,snapshot['source']=='synthetic')
        financial = houses[home] if employment['state']!='na' else result('na','outside_scope')
        gaps = []
        for z in tables['zemis']:
            a = z.get('Arbeitsbeginn')
            b = z.get('Verpflichtet bis') or '9999'
            if a and a<=snapshot['asof'] and not any(w.get('Von') and w['Von']<=b and (w.get('Bis') or '9999')>=a for w in tables['work']):
                gaps.append(z['_line'])
        cases.append(dict(id=pid,worker=person.get('Fallführung') or '–',home=home,entry=entry,age=age,
            status=status,school_years=person.get('Schuljahre vor Einreise'),goals=(language,employment,financial),tables=tables,gaps=gaps,end=end))
    return cases


A1_TOTALS = ('people','scope_in','scope_out','scope_review','due_now','upcoming_due','due_unknown',
             'a1_attainment','met','late','overdue','review')


def a1_totals(cases):
    totals = Counter()
    for case in cases:
        goal = case['goals'][0]
        scope = goal['scope']
        totals['people'] += 1
        totals[scope] += 1
        if scope=='scope_in':
            totals[{True:'due_now',False:'upcoming_due',None:'due_unknown'}[goal.get('due')]] += 1
        if goal['achieved']:
            totals['a1_attainment'] += 1
        metric = {'achieved':'met','late':'late','overdue':'overdue','review':'review'}.get(goal['state'])
        if metric:
            totals[metric] += 1
    return [totals[key] for key in A1_TOTALS]


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


def factors(cases, asof, dimension, intake_categories=None):
    """Fixed synthetic partitions restricted to complete A1 follow-up."""
    groups = defaultdict(list)
    unknown = 0
    eligible = 0
    for case in cases:
        goal = case['goals'][0]
        if goal['state']=='na' or not goal['deadline'] or goal['deadline']>asof:
            continue
        eligible += 1
        if goal['state']=='review':
            unknown += 1
            continue
        if dimension=='schooling':
            value = case.get('school_years')
            group = '0–8' if isinstance(value,(int,float)) and value<=8 else '9+' if isinstance(value,(int,float)) else None
        elif dimension=='intake':
            group = (intake_categories or {}).get(case['id'])
        elif dimension=='course':
            group = 'course_yes' if any(r.get('Art') in ('Förderangebot Sprache','Sprachkurs im erweiterten Verfahren (N)') and r.get('Start')
                      and r['Start']<=goal['deadline'].isoformat() for r in case['tables']['education']) else 'course_none'
        else:
            age = case.get('age')
            group = ('16–29' if age<30 else '30–44' if age<45 else '45+') if age is not None else None
        if group is None:
            unknown += 1
            continue
        groups[group].append(goal['state']=='achieved')
    results = []
    for label,outcomes in sorted(groups.items()):
        n = len(outcomes)
        k = sum(outcomes)
        if min(n,k,n-k)<MIN_GROUP:
            results.append((label,None,None,None))
            continue
        rate = k/n
        z = 1.96
        d = 1+z*z/n
        mid = (rate+z*z/(2*n))/d
        radius = z*sqrt((rate*(1-rate)+z*z/(4*n))/n)/d
        results.append((label,n,k,(mid-radius,mid+radius)))
    return results,eligible,unknown
