"""Allowlisted retrieval and aggregate-only time series evaluation."""
from dataclasses import dataclass
from datetime import date
from random import Random
from statistics import mean
from math import ceil

from .rules import analysis

IAS = 'https://www.sem.admin.ch/de/integrationsagenda'
MONITOR = 'https://www.sem.admin.ch/de/monitoring-integrationsfoerderung'
BERN = 'https://www.bern.ch/politik-und-verwaltung/stadtverwaltung/bss/sozialamt/asylsozialdienst'
FSO = 'https://www.bfs.admin.ch/en/newnsb/YskdJK6LxRTM'

SOURCES = {
    'a1': (MONITOR,'Sprachkompetenzen / Compétences linguistiques','ASD challenge, pp. 1–2 (November 2026)',
        ('Für VA/FL ab 16 gilt im Berner Challenge-Bericht eine A1-Frist von drei Jahren ab Einreise. Zertifizierung (telc/fide), Muttersprache, Schweizer Schulbesuch oder abgeschlossene Ausbildung sind genannte Nachweise.',
         'The Bern challenge applies a three-year A1 deadline from entry for VA/FL aged 16+. It lists telc/fide, mother tongue, Swiss schooling and completed education as evidence.',
         'Le défi bernois prévoit un délai A1 de trois ans après l’arrivée pour les AP/R dès 16 ans. Il cite telc/fide, langue maternelle, scolarité suisse et formation achevée.')),
    'work': (IAS,'Integrationsagenda Schweiz','ASD challenge, pp. 1–2 (November 2026)',
        ('Der Berner Challenge-Bericht verlangt mindestens 60 % Beschäftigung während sechs Monaten ohne Unterbruch oder eine Ausbildung der Sekundarstufe II/Tertiärstufe vor Zuständigkeitsende.',
         'The Bern challenge specifies uninterrupted employment at 60% or more for six months, or upper-secondary/tertiary education before responsibility ends.',
         'Le défi bernois prévoit six mois de travail sans interruption à 60 % ou plus, ou une formation du secondaire II ou du tertiaire avant la fin de la prise en charge.')),
    'household': (BERN,'Asylsozialdienst','ASD challenge, pp. 1–2 (November 2026)',
        ('Der Berner Challenge-Bericht nennt zwölf Monate ohne Sozialhilfe für den gesamten Haushalt vor Zuständigkeitsende. Die Demo verwendet die Dossier-Nr.',
         'The Bern challenge specifies twelve months without social assistance for the entire household before responsibility ends. The demo links via the case-file number.',
         'Le défi bernois prévoit douze mois sans aide sociale pour tout le ménage avant la fin de la prise en charge. La démo utilise le numéro de dossier.')),
    'scenario2027': (BERN,'Asylsozialdienst Stadt Bern','ASD challenge, pp. 1–2 (November 2026)',
        ('Die Challenge nennt für VA und F-FL sieben Jahre ab Einreise und fünf Jahre ab 1. Januar 2027. Die betroffenen Übergangskohorten sind zu bestätigen.',
         'The challenge states seven years from entry for VA and F-FL, then five years from 1 January 2027. Transitional cohorts require confirmation.',
         'Le défi indique sept ans après l’arrivée pour les AP et les réfugiés admis provisoirement, puis cinq ans dès le 1er janvier 2027. Les cohortes transitoires restent à confirmer.')),
}

@dataclass(frozen=True)
class RuleSource:
    topic: str
    version: str
    available_from: date
    effective_from: date | None
    authority: int
    owner: str
    citation: str
    context_url: str
    section: str
    answers: tuple[str,str,str]


RULE_INDEX = tuple(
    RuleSource(topic,'challenge-2026.11',date(2026,11,20),
               date(2027,1,1) if topic=='scenario2027' else None,
               100,'Stadt Bern ASD',citation,url,section,answers)
    for topic,(url,section,citation,answers) in SOURCES.items()
)
RULE_DATES = ('2026-11-20','2027-01-01')
AGGREGATE_INTENTS = ('entry_cohort','strongest_cohort','monthly_change')


@dataclass(frozen=True)
class RuleQuestion:
    topic: str
    language: int
    asof: str = RULE_DATES[0]

@dataclass(frozen=True)
class AggregateQuestion:
    intent: str

@dataclass(frozen=True)
class IntakeQuestion:
    category: str

CATEGORIES = ('schooling','course','scheduling','housing')
LANGUAGES = (0,1,2)


def retrieve_rule(question,index=RULE_INDEX):
    asof = date.fromisoformat(question.asof)
    hits = [r for r in index if r.topic==question.topic and r.available_from<=asof]
    if not hits:
        return {'mode':'insufficient'}
    current = max((r.authority,r.available_from) for r in hits)
    top = [r for r in hits if (r.authority,r.available_from)==current]
    if len({r.answers for r in top})>1:
        return {'mode':'conflict','citations':tuple(r.citation for r in top)}
    source = top[0]
    return {'text':source.answers[question.language],'source':source.citation,'section':source.section,
            'context_url':source.context_url,'mode':'retrieval_only','owner':source.owner,
            'version':source.version,'available_from':source.available_from.isoformat(),
            'effective_from':source.effective_from.isoformat() if source.effective_from else None,
            'upcoming':bool(source.effective_from and asof<source.effective_from)}


def gateway(request, snapshot=None, cases=(), trend=()):
    """Release only allowlisted source excerpts or suppressed aggregate values."""
    if (type(request) is RuleQuestion and request.topic in SOURCES and type(request.language) is int
            and request.language in LANGUAGES and request.asof in RULE_DATES):
        return retrieve_rule(request)
    if type(request) is AggregateQuestion and request.intent in AGGREGATE_INTENTS and snapshot:
        if request.intent=='monthly_change':
            points = [(month,n,k) for month,n,k in trend if n and k is not None]
            if len(points)!=2:
                return {'mode':'insufficient','snapshot':snapshot}
            return {'mode':'deterministic','snapshot':snapshot,'points':points,
                    'delta':points[-1][2]-points[0][2],'window':'monthly_snapshots'}
        _,_,released = analysis(cases,date.fromisoformat(snapshot),'year')
        if not released:
            return {'mode':'insufficient','snapshot':snapshot}
        rank = max if request.intent=='strongest_cohort' else min
        rate = rank(k/n for _,n,_,k,_ in released)
        matching = [(y,n,k) for y,n,_,k,_ in released if k/n==rate]
        y,n,k = matching[0]
        return {'mode':'deterministic','year':y,'denominator':n,'count':k,'groups':matching,
                'window':'completed_follow_up','snapshot':snapshot}
    if type(request) is IntakeQuestion and request.category in CATEGORIES:
        return {'mode':'local_classification','category':request.category,'approval_required':True}
    raise ValueError('privacy_policy_denied')


def observations(seed=2026, n=48):
    """Publicly reproducible synthetic monthly planning counts, Jan 2022 onward."""
    generator = Random(seed)
    return [max(1,round(20+0.48*i+3*(i%12>=8)+generator.gauss(0,2.1))) for i in range(n)]


def linear(values):
    series = values[-12:]
    xbar = (len(series)-1)/2
    ybar = mean(series)
    slope = sum((i-xbar)*(v-ybar) for i,v in enumerate(series))/sum((i-xbar)**2 for i in range(len(series)))
    return max(0,ybar+slope*(len(series)-xbar))


def backtest(values=None):
    if values is None:
        values = observations()
    if len(values)<42 or any(type(x) is not int or x<0 for x in values):
        return {'mode':'insufficient'}
    candidates = {'last': lambda v:v[-1],'seasonal':lambda v:v[-12],'trend':linear}
    split = len(values)-12
    validation = range(18,split-6)
    gate = range(split-6,split)
    evaluation = range(split,len(values))
    def residuals(name, window):
        return [abs(values[i]-candidates[name](values[:i])) for i in window]
    selected = min(candidates,key=lambda name:mean(residuals(name,validation)))
    winner = selected
    scores = {name:round(mean(residuals(name,evaluation)),2) for name in candidates}
    baseline = min(('last','seasonal'),key=lambda name:mean(residuals(name,validation)))
    gate_mae = {name:round(mean(residuals(name,gate)),2) for name in candidates}
    if mean(residuals(winner,gate))>=mean(residuals(baseline,gate)):
        winner = baseline
    errors = sorted(residuals(winner,validation))
    width = errors[min(len(errors)-1, ceil((len(errors)+1)*.9)-1)]
    estimate = round(candidates[winner](values))
    return {'model':winner,'est':estimate,'lo':max(0,round(estimate-width)), 'hi':round(estimate+width),
            'mae':scores,'heldout':len(evaluation),'coverage':round(mean(e<=width for e in residuals(winner,evaluation)),2),
            'horizon':1,'values':values,'selected':selected,'baseline':baseline,'gate_mae':gate_mae,
            'validation_months':len(validation),'gate_months':len(gate)}


def read_aggregate_series(blob):
    """Import a consecutive month/count series with no row-level fields."""
    from csv import reader
    from io import StringIO
    from datetime import date
    from .rules import months
    if len(blob)>32768:
        raise ValueError('series_size')
    rows = reader(StringIO(blob.decode('utf-8-sig')))
    if next(rows,None)!=['month','count']:
        raise ValueError('series_header')
    result = []
    previous = None
    for row in rows:
        if len(row)!=2 or len(row[0])!=7 or len(row[1])>8 or not row[1].isascii() or not row[1].isdigit():
            raise ValueError('series_value')
        current = date.fromisoformat(row[0]+'-01')
        if previous and current!=months(previous,1):
            raise ValueError('series_month_gap')
        result.append([row[0],int(row[1])])
        previous = current
    if not 42<=len(result)<=240:
        raise ValueError('series_length')
    return result
