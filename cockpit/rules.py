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
def load_responsibility_policy(path):
    policy = json.loads(Path(path).read_text())
    for key in ('refugee_application_months','temporary_admission_entry_months','transition_entry_months'):
        if type(policy[key]) is not int or not 1<=policy[key]<=240:
            raise ValueError('Invalid responsibility policy duration')
    date.fromisoformat(policy['transition_effective_date'])
    if policy['transition_cohort'] not in ('all_va_f_fl','entry_on_or_after_effective_date') or not str(policy['version']).strip():
        raise ValueError('Invalid responsibility policy')
    return policy


RESPONSIBILITY_POLICY = load_responsibility_policy(os.getenv('COCKPIT_RESPONSIBILITY_POLICY') or
                                                   Path(__file__).with_name('responsibility-policy.json'))
WORK_GOAL = 'Aufnahme Ausbildung / Erwerbstätigkeit'
HOUSEHOLD_GOAL = 'Finanzielle Unabhängigkeit'
APPLICATION_EVENTS = {'Asylgesuch in CH (Bund direkt, Kat. I)','Asylgesuch in CH (Kt normal, Kat. III)'}
MIN_GROUP = max(3,int(os.getenv('COCKPIT_MIN_GROUP','8')))
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


# Demo assumption (ASD to confirm): the Erwerb export has no labour-market field. Employment
# ('unselbstständig' / 'selbstständig') counts as first labour market unless the employer or remark
# names an employment or integration programme, which is excluded rather than counted.
SECOND_MARKET = re.compile(r'2\.\s*Arbeitsmarkt|Beschäftigungsprogramm|Beschäftigungsangebot|Integrationsprogramm|Arbeitsintegration',re.I)
PRIMARY_STATUSES = {'unselbstständig','selbstständig','1. Arbeitsmarkt'}


def primary_market(row):
    remark = ' '.join(str(row.get(k) or '') for k in ('Bemerkungen','Arbeitgeber Name'))
    return row.get('Erwerbsstatus') in PRIMARY_STATUSES and not SECOND_MARKET.search(remark)


def goal2(tables, asof, start, end, synthetic=False):
    if not end:
        return result('review','missing_end')
    cutoff = min(end,asof)
    candidates = [r for r in tables['work'] if (not r.get('Von') or r['Von']<=cutoff.isoformat())
                  and (not r.get('Bis') or r['Bis']>=start.isoformat())]
    jobs, unresolved = [], []
    for row in candidates:
        percent = row.get('Pensum %')
        if not isinstance(percent,(int,float)) or not 0<=percent<=100:
            unresolved.append(row)
        elif percent>=60:
            if row.get('Von') and primary_market(row):
                jobs.append(row)
            elif row.get('Von') and SECOND_MARKET.search(' '.join(str(row.get(k) or '') for k in ('Bemerkungen','Arbeitgeber Name'))):
                continue
            else:
                unresolved.append(row)
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
    if unresolved:
        return result('review','market_unknown',end,evidence=[('work',r['_line']) for r in unresolved])
    undated_education = [r for r in tables['education'] if r.get('Art') in ('Sek II','Tertiär') and not r.get('Start')]
    if undated_education:
        return result('review','education_unknown',end,evidence=[('education',r['_line']) for r in undated_education])
    evidence = [('work',line) for _,_,lines in spans for line in lines]
    reason = 'employment_gap' if len(spans)>1 else 'check_continuity'
    return judgement(asof,end,None,evidence,reason,earliest)


def goal3(household, members, assistance, end, asof, synthetic):
    if not end:
        return result('review','household_end_unknown')
    if not synthetic or not members or any(not r.get('Dossierperson Von') for r in members):
        return result('review','coverage_unknown',end)
    cut = min(end,asof)
    periods = [(as_date(r['Dossierperson Von']),as_date(r.get('Dossierperson Bis')),r['_line']) for r in members]
    if not any(a<=cut and (b is None or cut<=b) for a,b,_ in periods):
        return result('review','membership_unknown',end)
    # Conservative demo rule: start again at the most recent observed change in composition.
    starts = {a for a,_,_ in periods if a<=cut}
    departures = {b+DAY for _,b,_ in periods if b is not None and b<cut}
    first = max(starts|departures)
    changed = len(starts)>1 or bool(departures)
    evidence = [('membership',line) for a,b,line in periods if a<=cut]
    support_types = {'Sozialhilfe','Nothilfe','Keine Unterstützung'}
    uncertain = [r for r in assistance if r.get('Unterstützung') not in support_types or
                 (r['Unterstützung']!='Keine Unterstützung' and not r.get('Finanzielle Unterstützung Gültig von'))]
    if uncertain:
        return result('review','coverage_unknown',end,evidence=evidence+[('support',r['_line']) for r in uncertain])
    support = intervals([r for r in assistance if r['Unterstützung']!='Keine Unterstützung'],
                        'Finanzielle Unterstützung Gültig von','Finanzielle Unterstützung Gültig bis',first,cut)
    cursor = first
    attained = None
    for a,b,lines in support:
        evidence.extend(('support',line) for line in lines)
        if months(cursor,12)<a:
            attained = months(cursor,12)
            break
        cursor = max(cursor,b+DAY)
    candidate = months(cursor,12)
    attained = attained or (candidate if candidate<=cut else None)
    reason = 'support_free' if attained else 'membership_reset' if changed and cursor==first else 'support_check'
    return judgement(asof,end,attained,evidence,reason,candidate if cut<candidate<=end else None) | {'period_start':cursor}


def recorded(goal, rows, name, asof):
    matches = [(as_date(r.get('Erreicht am')),r['_line']) for r in rows
               if r.get('Art')==name and (not r.get('Erreicht am') or r['Erreicht am']<=asof.isoformat())]
    return goal | {'official_dates':sorted({d for d,_ in matches if d}),
                   'official_undated':any(d is None for d,_ in matches),
                   'evidence':goal['evidence']+[('official',line) for _,line in matches]}


def reference_ends(status, entry, events):
    policy = RESPONSIBILITY_POLICY
    if status in {'B-FL','B-RSFL','B-SL'}:
        applications = {as_date(r.get('Ereignisdatum')) for r in events if r.get('Asylgeschäftsart') in APPLICATION_EVENTS}
        application = next(iter(applications)) if len(applications)==1 else None
        return (months(application,policy['refugee_application_months']) if application else None,None)
    if status in {'VA','F-FL'} and entry:
        transition = policy['transition_cohort']
        candidate = (transition=='all_va_f_fl' or
                     transition=='entry_on_or_after_effective_date' and entry>=as_date(policy['transition_effective_date']))
        return (months(entry,policy['temporary_admission_entry_months']),
                months(entry,policy['transition_entry_months']) if candidate else None)
    return None,None


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


def zemis_reconcile(zemis, jobs, asof):
    findings = []
    for z in zemis:
        begin = z.get('Arbeitsbeginn')
        end = z.get('Verpflichtet bis') or asof
        if begin and begin>asof:
            continue
        employer = (z.get('Betrieb') or '').casefold()
        possible = [w for w in jobs if w.get('Von') and w['Von']<=min(end,asof)
                    and (w.get('Bis') or asof)>=(begin or asof)]
        rows = [w['_line'] for w in possible]
        if not begin or (not possible and any(not w.get('Von') for w in jobs)):
            reason = 'zemis_dates_unknown'
        elif not possible:
            reason = 'zemis_no_overlap'
        elif employer and any((w.get('Arbeitgeber Name') or '').casefold()==employer for w in possible):
            continue
        else:
            reason = 'zemis_employer_unknown'
        findings.append((z['_line'],reason,rows))
    return findings


def payments(cases):
    outcomes = [defaultdict(list) for _ in range(3)]
    for case in cases:
        for i,goal in enumerate(case['goals']):
            if goal['state']!='na':
                outcomes[i][case['home'] if i==2 else case['id']].append(goal)
    summary = []
    for group in outcomes:
        verified = unpaid = review = 0
        for goals in group.values():
            first = goals[0]
            if first['state']=='achieved':
                dates = {d for g in goals for d in g.get('official_dates',())}
                if dates=={first['achieved']} and not any(g.get('official_undated') for g in goals):
                    verified += 1
                else:
                    unpaid += 1
            elif first['state']=='review':
                review += 1
        summary.append((verified,unpaid,review))
    return summary


def evaluate(snapshot, rows, candidate=False):
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
    cutoffs = {}
    for person in rows.get('clients',[]):
        pid = person['_person']
        tables = indexes[pid]
        entries = {as_date(r.get('Ereignisdatum')) for r in tables['events'] if r.get('Asylgeschäftsart')=='Aufenthalt (Einreise)'}
        entry = next(iter(entries)) if len(entries)==1 else None
        reference, transition = reference_ends(person.get('Verfahrensstand'),entry,tables['events'])
        cutoffs[pid] = entry,reference,transition,as_date(person.get('Zuständigkeitsende'))
    shared = {}
    if candidate:
        # A member without a dated entry follows the household's shifted cutoff when the exported ends agree.
        members = defaultdict(list)
        for person in rows.get('clients',[]):
            members[person['Dossier-Nr.']].append(cutoffs[person['_person']])
        for home,group in members.items():
            moved = {t for _,_,t,_ in group if t is not None}
            if len({e for *_,e in group})==1 and len(moved)==1:
                shared[home] = next(iter(moved))
    for person in rows.get('clients',[]):
        pid = person['_person']
        entry,reference,transition,exported = cutoffs[pid]
        if (transition is None and person['Dossier-Nr.'] in shared and exported is not None
                and person.get('Verfahrensstand') in {'VA','F-FL'}):
            transition = shared[person['Dossier-Nr.']]
        effective = transition if candidate and transition is not None and exported is not None else exported
        ends[person['Dossier-Nr.']].add(effective)
        cutoffs[pid] = entry,reference,transition,effective
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
        entry,reference_end,transition_end,effective_end = cutoffs[pid]
        age = age_on(born,now)
        if status in OUT or (age is not None and age<16) or (start and start>now) or (end and end<now):
            employment=result('na','outside_scope')
        elif status not in ELIGIBLE or not born or not start or (active and active!={status}):
            employment=result('review','scope_unknown')
        else:
            employment = goal2(tables,now,start,effective_end,snapshot['source']=='synthetic')
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
            cutoff = next(iter(ends[home])) if len(ends[home])==1 else None
            houses[home] = goal3(home,family['membership'],family['support'],cutoff,now,snapshot['source']=='synthetic')
        financial = houses[home] if employment['state']!='na' else result('na','outside_scope')
        employment = recorded(employment,tables['official'],WORK_GOAL,now) if employment['state']!='na' else employment
        financial = recorded(financial,tables['official'],HOUSEHOLD_GOAL,now) if financial['state']!='na' else financial
        findings = zemis_reconcile(tables['zemis'],tables['work'],snapshot['asof'])
        gaps = [line for line,_,_ in findings]
        cases.append(dict(id=pid,worker=person.get('Fallführung') or '–',home=home,entry=entry,age=age,
            status=status,school_years=person.get('Schuljahre vor Einreise'),mother_tongue=person.get('Muttersprache'),goals=(language,employment,financial),tables=tables,household=household[home],gaps=gaps,zemis_findings=findings,end=end,effective_end=effective_end,
            reference_end=reference_end,transition_end=transition_end))
    return cases


# Ranked follow-up reasons. Lower rank first; ranks up to WEEK_RANK form "this week".
# Ordered by whether contact can still change the outcome, never by personal traits.
ACTION_RANKS = ('act_g1_risk','act_g1_record','act_g1_verify','act_goal_record','act_zemis','act_g2_verify',
                'act_g2_soon','act_scope','act_g3_review','act_g1_plan','act_g1_missed','act_none')
WEEK_RANK = ACTION_RANKS.index('act_g2_soon')


def next_action(case, asof):
    """The single most useful next step for one case, with the date it refers to."""
    language, work, household = case['goals']
    options = []
    if language['state']=='risk':
        options.append(('act_g1_risk',language['deadline'],0))
    if language['state'] in ('achieved','late') and language['reason']=='proof_difference':
        options.append(('act_g1_record',language['achieved'],0))
    if language['state']=='review' and language['reason']=='verify_proof':
        options.append(('act_g1_verify',language['deadline'],0))
    for index,goal in ((1,work),(2,household)):
        if goal['state'] in ('achieved','late') and not goal.get('official_dates') and not goal.get('official_undated'):
            options.append(('act_goal_record',goal['achieved'],index))
    if case['zemis_findings']:
        options.append(('act_zemis',None,1))
    if work['state']=='review' and work['reason']=='market_unknown':
        options.append(('act_g2_verify',work['deadline'],1))
    if work['earliest'] and (work['earliest']-asof).days<=60:
        options.append(('act_g2_soon',work['earliest'],1))
    if any(g['state']=='review' and g['reason'] in ('scope_unknown','entry_unknown','missing_end') for g in (language,work)):
        options.append(('act_scope',None,0))
    if household['state']=='review':
        options.append(('act_g3_review',household['deadline'],2))
    if language['state']=='ontrack' and language['deadline'] and (language['deadline']-asof).days<=365:
        options.append(('act_g1_plan',language['deadline'],0))
    if language['state']=='overdue':
        options.append(('act_g1_missed',language['deadline'],0))
    options.append(('act_none',None,None))
    key,when,goal = min(options,key=lambda o:ACTION_RANKS.index(o[0]))
    return dict(key=key,rank=ACTION_RANKS.index(key),when=when,goal=goal,
                days=(when-asof).days if when else None,week=ACTION_RANKS.index(key)<=WEEK_RANK)


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


FACTOR_DIMENSIONS = ('year','age','schooling','language_group','course','intake')


def wilson(k,n):
    rate = k/n
    z = 1.96
    d = 1+z*z/n
    mid = (rate+z*z/(2*n))/d
    radius = z*sqrt((rate*(1-rate)+z*z/(4*n))/n)/d
    return max(0,mid-radius),min(1,mid+radius)


def factor_group(case, dimension, goal, intake_categories):
    if dimension=='year':
        return case['entry'].year if case['entry'] else None
    if dimension=='schooling':
        value = case.get('school_years')
        return ('0–8' if value<=8 else '9+') if isinstance(value,(int,float)) else None
    if dimension=='intake':
        value = (intake_categories or {}).get(case['id'])
        return value or None
    if dimension=='language_group':
        value = case.get('mother_tongue')
        if not value:
            return None
        return value if value in {'Arabisch','Tigrinya','Dari','Deutsch','Französisch'} else 'other_language'
    if dimension=='course':
        eligible = [row for row in case['tables']['education']
                    if row.get('Art') in ('Förderangebot Sprache','Sprachkurs im erweiterten Verfahren (N)')]
        if any(not row.get('Start') for row in eligible) or not case['entry']:
            return None
        # Time from entry to the first language course: the factor ASD can act on.
        started = [as_date(r['Start']) for r in eligible if r['Start']<=goal['deadline'].isoformat()]
        if not started:
            return 'course_none'
        return 'course_early' if min(started)<=months(case['entry'],6) else 'course_late'
    age = case.get('age')
    return ('16–24' if age<25 else '25–34' if age<35 else '35+') if age is not None else None


def suppress_partition(groups):
    # Suppress sparse numerators and complements, plus a second row if exactly one is suppressed.
    suppressed = {label for label,states in groups.items()
                  if min(len(states),*(sum(state in positive for state in states)
                     for positive in ({'achieved'},{'achieved','late'},{'late','overdue','risk','ontrack'},
                                      {'overdue','risk','ontrack'}))) < MIN_GROUP}
    if len(suppressed)==1:
        alternatives = [(len(states),str(label),label) for label,states in groups.items() if label not in suppressed]
        if alternatives:
            suppressed.add(min(alternatives)[2])
    return suppressed


def analysis(cases,asof,dimension='year',intake_categories=None,goal_index=0):
    """Fixed partitions. The A1 denominator uses completed follow-up; G2/3 are observed-to-date."""
    groups = defaultdict(list)
    coverage = Counter()
    if goal_index==2:
        cases = {c['home']:c for c in cases if c['goals'][2]['state']!='na'}.values()
    for case in cases:
        goal = case['goals'][goal_index]
        if goal['state']=='na':
            continue
        if not goal['deadline']:
            coverage['missing'] += 1
            continue
        if goal['deadline']>asof:
            coverage['upcoming'] += 1
            if goal_index==0:
                continue
        if goal['state']=='review':
            coverage['missing'] += 1
            continue
        group = factor_group(case,dimension,goal,intake_categories) if goal_index==0 else goal['deadline'].year
        if group is None:
            coverage['missing'] += 1
            continue
        groups[group].append(goal['state'])
    suppressed = suppress_partition(groups)
    rows = []
    for label,states in sorted(groups.items()):
        if label in suppressed:
            rows.append((label,None,None,None,None))
            continue
        n = len(states)
        ontime = states.count('achieved')
        observed = ontime+states.count('late')
        rows.append((label,n,observed,ontime,wilson(ontime,n)))
    public = [r for r in rows if r[1] is not None]
    # Coverage bins are also subject to minimum-cell checks.
    protected = {key:(value if value>=MIN_GROUP else None) for key,value in coverage.items()}
    return rows,protected,public


def factors(cases,asof,dimension,intake_categories=None):
    rows,coverage,_ = analysis(cases,asof,dimension,intake_categories)
    return [(label,n,k,band) for label,n,_,k,band in rows],sum(row[1] or 0 for row in rows),coverage.get('missing')
