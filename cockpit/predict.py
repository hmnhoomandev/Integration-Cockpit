"""Local A1 outcome model: logistic regression trained on completed cases, validated by cross-validation.

Runs in-process on the cockpit machine. Nationality, mother tongue and gender are never features.
"""
from datetime import date
from math import exp, log
from random import Random

from .rules import MIN_GROUP, as_date, months

FEATURES = ('course_early','course_late','school_years','age_at_entry','latin','small_children')
COURSES = ('Förderangebot Sprache','Sprachkurs im erweiterten Verfahren (N)')


def course_status(case, until):
    started = [as_date(r['Start']) for r in case['tables']['education']
               if r.get('Art') in COURSES and r.get('Start') and r['Start']<=until.isoformat()]
    if not started or not case['entry']:
        return 'none'
    return 'early' if min(started)<=months(case['entry'],6) else 'late'


def raw_features(case, until, children):
    person = case['tables']['clients'][0] if case['tables']['clients'] else {}
    born = as_date(person.get('Geburtsdatum'))
    course = course_status(case, until)
    age = (case['entry']-born).days/365.25 if born and case['entry'] else None
    school = person.get('Schuljahre vor Einreise')
    return {'course_early':float(course=='early'),'course_late':float(course=='late'),
            'school_years':float(school) if isinstance(school,(int,float)) else None,
            'age_at_entry':age,'latin':float(person.get('Lateinisch alphabetisiert')=='Ja'),
            'small_children':float(case['home'] in children and (case['age'] or 0)>=20)}


def young_children(cases):
    return {c['home'] for c in cases if c['age'] is not None and c['age']<8}


def sigmoid(z):
    return 1/(1+exp(-max(-30,min(30,z))))


def fit(rows, labels, steps=250, rate=.5, penalty=.01):
    weights = [0.0]*(len(rows[0])+1)
    n = len(rows)
    for _ in range(steps):
        gradient = [0.0]*len(weights)
        for x,y in zip(rows,labels):
            error = sigmoid(weights[0]+sum(w*v for w,v in zip(weights[1:],x)))-y
            gradient[0] += error
            for i,v in enumerate(x,1):
                gradient[i] += error*v
        weights[0] -= rate*gradient[0]/n
        for i in range(1,len(weights)):
            weights[i] -= rate*(gradient[i]/n+penalty*weights[i])
    return weights


def auc(scores, labels):
    positives = [s for s,y in zip(scores,labels) if y]
    negatives = [s for s,y in zip(scores,labels) if not y]
    if not positives or not negatives:
        return None
    wins = sum((p>q)+.5*(p==q) for p in positives for q in negatives)
    return wins/(len(positives)*len(negatives))


class Model:
    """Trained on people whose A1 deadline has passed; predicts open cases."""

    def __init__(self, cases, asof):
        self.asof = asof
        self.children = young_children(cases)
        done = [c for c in cases if c['goals'][0].get('due') and c['goals'][0]['state'] in ('achieved','late','overdue')]
        raw = [raw_features(c,c['goals'][0]['deadline'],self.children) for c in done]
        self.labels = [int(c['goals'][0]['state']=='achieved') for c in done]
        known = [r['school_years'] for r in raw if r['school_years'] is not None]
        self.school_default = sum(known)/len(known) if known else 0
        ages = [r['age_at_entry'] for r in raw if r['age_at_entry'] is not None]
        self.age_default = sum(ages)/len(ages) if ages else 30
        columns = list(zip(*(self.vector(r,scale=False) for r in raw))) if raw else []
        self.mean = [sum(col)/len(col) for col in columns]
        self.scale = [max(1e-6,(sum((v-m)**2 for v in col)/len(col))**.5) for col,m in zip(columns,self.mean)]
        self.rows = [self.vector(r) for r in raw]
        self.base = sum(self.labels)/len(self.labels) if self.labels else None
        self.ready = len(self.rows)>=40 and 0<sum(self.labels)<len(self.labels)
        self.weights = fit(self.rows,self.labels) if self.ready else None
        self.validation = self.cross_validate() if self.ready else None
        self.done = list(zip(done,raw))

    def vector(self, r, scale=True):
        values = [r['course_early'],r['course_late'],
                  self.school_default if r['school_years'] is None else r['school_years'],
                  self.age_default if r['age_at_entry'] is None else r['age_at_entry'],
                  r['latin'],r['small_children']]
        return [(v-m)/s for v,m,s in zip(values,self.mean,self.scale)] if scale else values

    def score(self, x, weights=None):
        w = weights or self.weights
        return sigmoid(w[0]+sum(a*b for a,b in zip(w[1:],x)))

    def cross_validate(self, folds=5):
        order = list(range(len(self.rows)))
        Random(7).shuffle(order)
        scores = [0.0]*len(order)
        for k in range(folds):
            test = set(order[k::folds])
            train = [i for i in order if i not in test]
            w = fit([self.rows[i] for i in train],[self.labels[i] for i in train])
            for i in test:
                scores[i] = self.score(self.rows[i],w)
        brier = sum((s-y)**2 for s,y in zip(scores,self.labels))/len(scores)
        baseline = sum((self.base-y)**2 for y in self.labels)/len(self.labels)
        return {'n':len(self.rows),'auc':auc(scores,self.labels),'brier':brier,'baseline_brier':baseline,
                'skill':1-brier/baseline if baseline else None}

    def explain(self, case):
        """Probability, the factors that move it most, a what-if and similar completed cases."""
        goal = case['goals'][0]
        if not self.ready or goal['state'] not in ('ontrack','risk') or not goal.get('deadline'):
            return None
        raw = raw_features(case,self.asof,self.children)
        x = self.vector(raw)
        probability = self.score(x)
        effects = sorted(((name,w*v) for name,w,v in zip(FEATURES,self.weights[1:],x)),key=lambda e:-abs(e[1]))
        factors = [(name,effect) for name,effect in effects if abs(effect)>=.15][:3]
        def group(**fixed):
            # Completed cases in the same situation; suppressed below MIN_GROUP or with a tiny numerator/complement.
            labels = [label for (c,r),label in zip(self.done,self.labels)
                      if all(r[k]==v for k,v in fixed.items()) and (r['age_at_entry'] or 0)//10==(raw['age_at_entry'] or 0)//10]
            return (len(labels),sum(labels)) if len(labels)>=MIN_GROUP and MIN_GROUP<=sum(labels)<=len(labels)-MIN_GROUP else None
        peers = group(course_early=raw['course_early'],course_late=raw['course_late'])
        scenario = None
        if not raw['course_early']:
            scenario = ('scenario_course_now',group(course_early=1.0,course_late=0.0))
        return {'probability':probability,'factors':factors,'scenario':scenario,'peers':peers,'raw':raw,
                'validation':self.validation,'base':self.base}


_cache = {}


def model_for(snapshot_id, cases, asof):
    key = (snapshot_id,asof)
    if key not in _cache:
        if len(_cache)>8:
            _cache.clear()
        _cache[key] = Model(cases,date.fromisoformat(asof) if isinstance(asof,str) else asof)
    return _cache[key]
