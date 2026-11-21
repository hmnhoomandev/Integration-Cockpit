"""Server-rendered German, English and French interface."""
from html import escape
from urllib.parse import urlencode
from itertools import chain

from . import rules
from .data import MONTHS
from .insights import SOURCES, FSO

LOCALES = ('de-CH','en','fr-CH')
COPY = {
 'overview':('Übersicht','Overview','Vue d’ensemble'),
 'queue':('Fallführung','Casework','Suivi des dossiers'),
 'case':('Falldetails','Case details','Détail du dossier'),
 'reports':('Daten & Berichte','Data & reports','Données et rapports'),
 'ai':('Regelassistent','Rules assistant','Assistant des règles'),
 'forecast':('Prognose','Forecast','Prévisions'),
 'intake':('Situationsanalyse','Intake review','Analyse de situation'),
 'login':('Anmelden','Sign in','Se connecter'),
 'logout':('Abmelden','Sign out','Se déconnecter'),
 'username':('Benutzername','Username','Identifiant'),
 'password':('Passwort','Password','Mot de passe'),
 'invalid_login':('Anmeldung fehlgeschlagen','Sign-in failed','Échec de connexion'),
 'demo':('Hackathon · synthetische Daten','Hackathon · synthetic data','Hackathon · données synthétiques'),
 'local':('Lokaler Import','Local import','Importation locale'),
 'lead':('Integrationsziele, Fristen und Nachweise im Überblick.','Track integration goals, deadlines and evidence.','Suivez les objectifs, délais et justificatifs d’intégration.'),
 'snapshot':('Stichtag','Report date','Date de référence'),
 'people':('Personen','People','Personnes'),
 'homes':('Haushalte','Households','Ménages'),
 'met':('A1 fristgerecht','A1 on time','A1 dans les délais'),
 'follow':('A1 mit Handlungsbedarf','A1 needs follow-up','A1 à suivre'),
 'quality':('ZEMIS-Abweichungen','ZEMIS discrepancies','Écarts ZEMIS'),
 'a1':('Sprache A1','Language A1','Langue A1'),
 'work':('Arbeit & Ausbildung','Work & education','Travail et formation'),
 'household':('Finanzielle Selbstständigkeit','Financial independence','Autonomie financière'),
 'goals':('Integrationsziele','Integration goals','Objectifs d’intégration'),
 'groups':('A1 nach Einreisejahr','A1 by entry year','A1 par année d’arrivée'),
 'eligible':('Auswertbare Personen','Evaluable people','Personnes évaluables'),
 'year':('Einreisejahr','Entry year','Année d’arrivée'),
 'ontrack':('Auf Kurs','On track','En bonne voie'),
 'achieved':('Fristgerecht','On time','Dans les délais'),
 'late':('Verspätet erreicht','Achieved late','Atteint en retard'),
 'overdue':('Frist überschritten','Overdue','Délai dépassé'),
 'risk':('Handlungsbedarf','Needs follow-up','Suivi nécessaire'),
 'review':('Prüfen','Review','À vérifier'),
 'na':('Nicht relevant','Out of scope','Hors périmètre'),
 'proof':('Sprachnachweis liegt vor','Language evidence recorded','Justificatif linguistique enregistré'),
 'proof_difference':('Nachweis und offizielle Zielerreichung abgleichen','Reconcile proof with official attainment','Vérifier la cohérence avec le résultat officiel'),
 'verify_proof':('Sprachnachweis verifizieren','Verify language evidence','Vérifier le justificatif linguistique'),
 'missing_proof':('Zertifikat oder Schulnachweis klären','Check certificate or schooling evidence','Vérifier le certificat ou la scolarité'),
 'outside_scope':('Ausserhalb der Zielgruppe','Outside the target population','Hors population cible'),
 'scope_unknown':('Status, Alter oder Zuständigkeit prüfen','Review status, age or responsibility','Vérifier statut, âge ou prise en charge'),
 'entry_unknown':('Einreisedatum klären','Confirm date of entry','Confirmer la date d’arrivée'),
 'missing_end':('Ende der Zuständigkeit klären','Confirm end of responsibility','Confirmer la fin de prise en charge'),
 'employment':('Beschäftigungsdauer belegt','Employment duration evidenced','Durée d’emploi attestée'),
 'education':('Ausbildung der Sek II oder Tertiärstufe','Upper-secondary or tertiary enrolment','Formation du secondaire II ou du tertiaire'),
 'check_continuity':('Beschäftigungsdauer oder Ausbildung prüfen','Check employment continuity or education','Vérifier la continuité de l’emploi ou la formation'),
 'coverage_unknown':('Haushaltsabdeckung oder Stichtag ungeklärt','Household coverage or cutoff requires review','Couverture du ménage ou échéance à vérifier'),
 'support_free':('Unterstützungsfreier Zeitraum berechnet','Support-free interval calculated','Période sans aide calculée'),
 'support_check':('Unterstützungsverlauf prüfen','Check assistance history','Vérifier l’historique d’aide'),
 'suppressed':('Unterdrückt','Suppressed','Masqué'),
 'group_note':('Feste Kohorten; kleine Zellen werden unterdrückt. Die Werte zeigen Zusammenhänge.','Fixed cohorts with small-cell suppression. Rates are descriptive associations.','Cohortes fixes avec masquage des petits effectifs. Les taux sont descriptifs.'),
 'deadline':('Frist','Deadline','Échéance'),
 'attained':('Erreicht am','Attainment date','Date d’atteinte'),
 'scenario':('Frühester Termin bei unverändertem Verlauf','Earliest possible date if circumstances continue','Première date possible si la situation se poursuit'),
 'reason':('Nächster Prüfschritt','Next review action','Prochaine vérification'),
 'evidence':('Quellenzeilen','Source rows','Lignes source'),
 'worker':('Fallführung','Assignment','Affectation'),
 'search':('Suchen','Search','Rechercher'),
 'previous':('Zurück','Previous','Précédent'),
 'next':('Weiter','Next','Suivant'),
 'empty':('Keine passenden Daten','No matching data','Aucune donnée correspondante'),
 'export':('Excel herunterladen','Download Excel','Télécharger Excel'),
 'coverage':('Importierte Quelldaten','Imported sources','Sources importées'),
 'rows':('Zeilen','Rows','Lignes'),
 'import':('Monatsexport importieren','Import monthly export','Importer les exports mensuels'),
 'synthetic_load':('Synthetischen Monat erneut einlesen','Re-import synthetic month','Réimporter le mois synthétique'),
 'choose':('Stichtag laden','Load report date','Charger la date de référence'),
 'uploaded':('Import abgeschlossen','Import complete','Import terminé'),
 'repeated':('Identischer Export bereits vorhanden','Identical export already present','Export identique déjà présent'),
 'rejected':('Import abgelehnt. Der letzte Stichtag bleibt verfügbar.','Import rejected. The last snapshot remains available.','Import refusé. Le dernier instantané reste disponible.'),
 'no_access':('Zugriff verweigert','Access denied','Accès refusé'),
 'retrieval':('Lokale Quellenabfrage · ohne Sprachmodell','Local retrieval · no language model','Recherche locale · sans modèle linguistique'),
 'source':('Quelle','Source','Source'),
 'privacy':('Datenschutz-Vorschau','Privacy preview','Aperçu de confidentialité'),
 'before':('Synthetische Eingabe','Synthetic input','Entrée synthétique'),
 'after':('Freigegebene Felder','Permitted fields','Champs autorisés'),
 'aggregate':('Einreisekohorte mit niedrigster beobachteter Rate','Entry cohort with the lowest observed rate','Cohorte d’arrivée au taux observé le plus faible'),
 'model':('Zeitliche Validierung · synthetische Monatswerte','Time-ordered validation · synthetic monthly counts','Validation temporelle · séries mensuelles synthétiques'),
 'public':('Öffentlicher Vergleichswert','Public benchmark','Indicateur public'),
 'public_note':('Schweiz, 2025: mehr als vier von zehn Personen ab 15 mit Migrationshintergrund. Andere Grundgesamtheit als beim ASD.','Switzerland, 2025: more than four in ten people aged 15+ had a migration background. This population differs from ASD’s.','Suisse, 2025 : plus de quatre personnes de 15 ans ou plus sur dix issues de la migration. Population différente de celle de l’ASD.'),
 'interval':('Prognoseintervall','Prediction interval','Intervalle de prévision'),
 'heldout':('Testmonate','Held-out months','Mois de test'),
 'data_card':('Datendokumentation','Data card','Fiche de données'),
 'policy':('Regelversion und Annahmen','Rule version and assumptions','Version des règles et hypothèses'),
 'assumptions':('Deutsch als Demosprache; Alter am Stichtag; Ausbildungsbeginn zählt; keine Zusammenrechnung paralleler Stellen; Unterstützungsabdeckung nur für synthetische Daten als vollständig behandelt.','German is the demo proof language; age is measured on the report date; enrolment qualifies; concurrent jobs are evaluated separately; complete assistance coverage is assumed for synthetic data only.','L’allemand sert de langue de référence pour la démo. Âge à la date du rapport, début de formation retenu, emplois simultanés évalués séparément et couverture complète supposée pour les seules données synthétiques.'),
 'review_save':('Kategorie bestätigen','Confirm category','Confirmer la catégorie'),
 'pdf_review':('PDF lokal auswerten','Review PDF locally','Examiner le PDF localement'),
 'manual':('Manuelle Prüfung erforderlich','Manual review required','Vérification manuelle nécessaire'),
 'category':('Kategorie','Category','Catégorie'),
 'scenario2027':('Szenario 2027','2027 scenario','Scénario 2027'),
 'tariff':('Illustrative Abgeltung pro fristgerechtes A1','Illustrative payment per on-time A1','Montant illustratif par A1 dans les délais'),
 'synthetic_only':('Nur Testdaten','Synthetic data only','Données synthétiques uniquement'),
 'schooling':('Schulbildung','Prior schooling','Scolarité antérieure'),
 'course':('Kursteilnahme','Course participation','Participation à un cours'),
 'scheduling':('Betreuungszeiten','Childcare scheduling','Horaires de garde'),
 'housing':('Wohnstabilität','Housing stability','Stabilité du logement'),
}


def esc(v):
    return escape(str(v if v is not None else '—'),quote=True)


def tr(lang,key):
    return COPY.get(key,(key,)*3)[lang]


def text(lang,key):
    return esc(tr(lang,key))


def href(path, **params):
    return esc(path+'?'+urlencode(params))


def table(headers, rows):
    return '<div class="tablewrap"><table><thead><tr>'+''.join(f'<th scope="col">{esc(h)}</th>' for h in headers)+'</tr></thead><tbody>'+''.join(
        '<tr>'+''.join(f'<td>{cell}</td>' for cell in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def heading(lang,key,detail=''):
    return f'<div class="heading"><h1>{text(lang,key)}</h1>{f"<p>{detail}</p>" if detail else ""}</div>'


def post(path,csrf,body,files=False):
    enctype=' enctype="multipart/form-data"' if files else ''
    return f'<form method="post" action="{esc(path)}"{enctype}><input type="hidden" name="csrf" value="{esc(csrf)}">{body}</form>'


def action(lang,key):
    return f'<button type="submit">{text(lang,key)}</button>'


def badge(lang,state):
    return f'<span class="badge {esc(state)}"><i></i>{text(lang,state)}</span>'


def layout(lang,active,body,account=None,csrf='',snapshot=None):
    menus = ['overview','queue','reports','ai','forecast','intake']
    if account:
        if account['role']=='worker':
            menus.remove('forecast')
        if account['role']=='manager':
            menus = [m for m in menus if m not in ('queue','intake')]
        if account['role']=='importer':
            menus = ['reports','intake','ai']
    nav = ''.join(f'<a href="/{key}" {"aria-current=page" if key==active else ""}>{text(lang,key)}</a>' for key in menus) if account else ''
    language = ''.join(f'<a lang="{locale}" href="/language/{locale}" {"aria-current=page" if i==lang else ""}>{locale[:2].upper()}</a>'
                       for i,locale in enumerate(LOCALES))
    date = f'<span class="snapshot">{text(lang,"snapshot")} <strong>{esc(snapshot["asof"])}</strong></span>' if snapshot else ''
    logout = post('/logout',csrf,action(lang,'logout')) if account else ''
    frame = f'<aside><a class="brand" href="/"><span aria-hidden="true">✳</span><div>Integrations-Cockpit<small>Bern</small></div></a><nav>{nav}</nav><div class="aside-bottom">{text(lang,"demo")}</div></aside>' if account else ''
    mode = 'dashboard' if account else 'signin'
    return f'''<!doctype html><html lang="{LOCALES[lang]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{text(lang,active)} · Integrations-Cockpit Bern</title><link rel="stylesheet" href="/static/app.css"></head>
<body class="{mode}">{frame}<div class="workspace"><header>{date}<div class="header-actions"><div class="languages">{language}</div>{logout}</div></header>
<main id="main">{body}</main></div></body></html>'''


def overview(lang,snapshot,cases,management):
    s = rules.counts(cases,0)
    metrics = (('people',len(cases)),('homes',len({c['home'] for c in cases})),('met',s['achieved']),
               ('follow',sum(s[key] for key in ('risk','overdue','review'))))
    if management and snapshot['source']!='synthetic':
        metrics = tuple((key,value if value>=rules.MIN_GROUP else '—') for key,value in metrics)
    kpis = ''.join(f'<article class="kpi"><span>{text(lang,k)}</span><strong>{v}</strong></article>' for k,v in metrics)
    goals = []
    for i,key in enumerate(('a1','work','household')):
        totals = rules.counts(cases,i)
        statuses = [(state,count) for state,count in totals.most_common() if snapshot['source']=='synthetic' or not management or count>=rules.MIN_GROUP]
        rows = ''.join(f'<li>{badge(lang,state)}<strong>{count}</strong></li>' for state,count in statuses)
        goals.append(f'<article class="panel"><h3>{text(lang,key)}</h3><ul class="breakdown">{rows}</ul></article>')
    groups = rules.group_metrics(cases)
    group_html = table([tr(lang,'year'),tr(lang,'eligible'),tr(lang,'met')],((esc(y),esc(n) if n else text(lang,'suppressed'),esc(k)) for y,n,k in groups))
    return f'''<section class="hero"><div class="hero-copy"><p class="eyebrow">{text(lang,'demo' if snapshot['source']=='synthetic' else 'local')}</p>
{heading(lang,'overview',text(lang,'lead'))}</div></section>
<div class="kpis">{kpis}</div><h2>{text(lang,'goals')}</h2><div class="three">{''.join(goals)}</div>
<section class="panel"><h2>{text(lang,'groups')}</h2><p>{text(lang,'group_note')}</p>{group_html}</section>'''


def queue(lang,cases,query,page,filter_state):
    limits = {'overdue':0,'risk':1,'review':2,'ontrack':3,'late':4,'achieved':5,'na':6}
    cases = [c for c in cases if query.casefold() in c['id'].casefold()
             and (not filter_state or c['goals'][0]['state']==filter_state)]
    cases.sort(key=lambda c:(limits[c['goals'][0]['state']],str(c['goals'][0]['deadline'] or '9999'),c['id']))
    offset = (page-1)*20
    options = ''.join(f'<option value="{key}" {"selected" if key==filter_state else ""}>{text(lang,key)}</option>' for key in limits)
    form = f'''<form class="inline" action="/queue"><label>{text(lang,'search')} <input name="q" value="{esc(query)}"></label>
<label>{text(lang,'a1')} <select name="state"><option value="">—</option>{options}</select></label>{action(lang,'search')}</form>'''
    rows = ((f'<a class="case-link" href="/case/{esc(c["id"])}">{esc(c["id"])}</a>',
             *(badge(lang,g['state']) for g in c['goals']),esc(c['goals'][0]['deadline']),text(lang,c['goals'][0]['reason']))
            for c in cases[offset:offset+20])
    pagination = '<div class="pagination">'
    if page>1:
        pagination += f'<a href="{href("/queue",q=query,state=filter_state,page=page-1)}">{text(lang,"previous")}</a>'
    if offset+20<len(cases):
        pagination += f'<a href="{href("/queue",q=query,state=filter_state,page=page+1)}">{text(lang,"next")}</a>'
    return heading(lang,'queue')+form+table(['ID',*(tr(lang,k) for k in ('a1','work','household','deadline','reason'))],rows)+pagination+'</div>'


def detail(lang,case):
    sections = []
    for key,g in zip(('a1','work','household'),case['goals']):
        ev = ', '.join(f'{esc(k)} #{line}' for k,line in g['evidence']) or '—'
        rows = [(tr(lang,'deadline'),g['deadline']),(tr(lang,'attained'),g['achieved']),(tr(lang,'scenario'),g['earliest'])]
        facts = ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k,v in rows)
        sections.append(f'<section class="panel"><h2>{text(lang,key)}</h2>{badge(lang,g["state"])}<p>{text(lang,g["reason"])}</p><dl>{facts}<dt>{text(lang,"evidence")}</dt><dd>{ev}</dd></dl></section>')
    return heading(lang,'case',esc(case['id']))+'<div class="three">'+''.join(sections)+'</div>'


def reports(lang,snapshot,history,role,csrf,hosted,notice='',issues=()):
    report = f'<a class="button" href="/export">{text(lang,"export")}</a>' if role!='importer' and snapshot else ''
    import_controls = ''
    if role in ('judge','importer'):
        button = action(lang,'synthetic_load')
        options = ''.join(f'<option>{d}</option>' for d in MONTHS)
        import_controls = post('/seed',csrf,f'<label>{text(lang,"snapshot")} <select name="date">{options}</select></label>{button}')
        if not hosted:
            import_controls += post('/import',csrf,
                f'<label>{text(lang,"snapshot")} <input name="date" type="date" required></label>'
                f'<label>Excel <input name="workbooks" type="file" accept=".xlsx" multiple required></label>{action(lang,"import")}',True)
    current = ''
    if snapshot:
        import json
        counts = json.loads(snapshot['inspected'])
        current = table([tr(lang,'source'),tr(lang,'rows')],((esc(k),esc(n)) for k,n in counts.items()))
    choices = ''.join(f'<option value="{r["id"]}">{esc(r["asof"])} · {text(lang,"demo" if r["source"]=="synthetic" else "local")}</option>' for r in history)
    history_form = post('/snapshot',csrf,f'<label>{text(lang,"snapshot")} <select name="id">{choices}</select></label>{action(lang,"choose")}') if choices else ''
    errors = ''.join(f'<li>{esc(k)} · #{i} · {text(lang,r)}</li>' for k,i,r in issues)
    feedback = f'<div class="feedback" role="status">{text(lang,notice)}<ul>{errors}</ul></div>' if notice else ''
    return heading(lang,'reports')+feedback+f'''
<section class="panel actions">{history_form}{import_controls}{report}</section>
<div class="two"><section class="panel"><h2>{text(lang,'coverage')}</h2>{current}</section>
<section class="panel"><h2>{text(lang,'policy')}</h2><p class="mono">{rules.VERSION}</p><p>{text(lang,'assumptions')}</p></section></div>'''


def assistant(lang,topic,result,aggregate):
    topics = ''.join(f'<a class="chip" href="/ai?topic={k}" {"aria-current=page" if k==topic else ""}>{text(lang,k)}</a>' for k in SOURCES)
    a = f'<strong>{aggregate["year"]}</strong> · {aggregate["count"]}/{aggregate["denominator"]} · {esc(aggregate["snapshot"])}' if aggregate and 'year' in aggregate else text(lang,'suppressed')
    return heading(lang,'ai',text(lang,'retrieval'))+f'''
<div class="chips">{topics}</div><section class="panel reading"><h2>{text(lang,topic)}</h2><p>{esc(result['text'])}</p>
<p class="source">{esc(result['source'])} · <a href="{esc(result['context_url'])}">{esc(result['section'])}</a></p></section>
<div class="two"><section class="panel"><h2>{text(lang,'privacy')}</h2><dl>
<dt>{text(lang,'before')}</dt><dd><code>DEMO-00001 · 08.04.1987 · A1</code></dd>
<dt>{text(lang,'after')}</dt><dd><code>{{"topic": "{esc(topic)}", "locale": "{LOCALES[lang]}"}}</code></dd></dl></section>
<section class="panel"><h2>{text(lang,'aggregate')}</h2><p>{a}</p><p>{text(lang,'group_note')}</p></section></div>'''


def forecast(lang,report,tariff,cases):
    values = report['values']
    top = max(values+[report['hi']])
    bars = ''.join(f'<meter min="0" max="{top}" value="{v}" aria-label="{i+1}: {v}">{v}</meter>'
                   for i,v in enumerate(values[-24:],len(values)-23))
    from .rules import months
    cohort = [case for case in cases if case['status'] in ('VA','F-FL') and case['entry'] and case['end']]
    changed = sum(months(c['entry'],60)!=c['end'] for c in cohort)
    met = sum(c['goals'][0]['state']=='achieved' for c in cases)
    checks = table(['Model','MAE'],((esc(k),esc(v)) for k,v in report['mae'].items()))
    status = f'{esc(report["model"])} · {text(lang,"heldout")} {report["heldout"]} · {report["coverage"]:.0%}'
    raw_values = ', '.join(map(str,values))
    return heading(lang,'forecast',text(lang,'model'))+f'''
<div class="two"><section class="panel reading"><h2>{text(lang,'interval')}</h2><strong class="forecast-value">{report['est']} <small>{report['lo']}–{report['hi']}</small></strong>
<p>{status}</p><div class="series" aria-hidden="true">{bars}</div><details><summary>{text(lang,'data_card')}</summary>
<p>2022-01 → 2025-12 · 48 · seed 2026 · SYN</p><p class="mono">{raw_values}</p></details></section>
<section class="panel"><h2>MAE</h2>{checks}</section></div>
<div class="two"><section class="panel"><h2>{text(lang,'public')}</h2><p>{text(lang,'public_note')}</p><a href="{FSO}">{text(lang,'source')} · BFS / FSO</a></section>
<section class="panel"><h2>{text(lang,'scenario2027')}</h2><p>VA / F-FL · 60 M · {changed}/{len(cohort)}</p>
<form action="/forecast"><label>{text(lang,'tariff')} <input type="number" name="rate" min="0" max="100000" value="{tariff}"></label>{action(lang,'choose')}</form>
<p>{met} × CHF {tariff:,} = <strong>CHF {met*tariff:,}</strong></p></section></div>'''


def login(lang,csrf,error=''):
    return '<section class="login-hero"><div><p class="eyebrow">'+text(lang,'demo')+'</p><h1>Integrations-<br>Cockpit Bern</h1><p>'+text(lang,'lead')+'</p></div></section><section class="login-card">'+heading(lang,'login')+(
        f'<p class="feedback" role="alert">{text(lang,error)}</p>' if error else '')+post('/login',csrf,
        f'<label>{text(lang,"username")}<input name="username" autocomplete="username" required></label>'
        f'<label>{text(lang,"password")}<input name="password" type="password" autocomplete="current-password" required></label>'
        +action(lang,'login'))+'</section>'


def export(lang,snapshot,cases,role):
    keys = ('a1','work','household')
    source = tr(lang,'demo' if snapshot['source']=='synthetic' else 'local')
    tabs = {'Metadata':[['Snapshot',snapshot['asof']],['Origin',source],['Rule version',rules.VERSION]]}
    for i,key in enumerate(keys):
        if i==2:
            selected = {c['home']:c for c in cases if c['goals'][i]['state']!='na'}.values()
        else:
            selected = cases
        summary = rules.counts(cases,i)
        tabs[tr(lang,key)] = chain([[tr(lang,key),tr(lang,'rows')]],
            ([tr(lang,s),n] for s,n in sorted(summary.items()) if role!='manager' or n>=rules.MIN_GROUP))
        if role!='manager':
            tabs[f'{i+1} · {tr(lang,"evidence")}'] = chain(
                [['ID',*[tr(lang,k) for k in ('worker','year','deadline','attained','reason','evidence')],tr(lang,'goals')]],
                ([c['home'] if i==2 else c['id'],c['worker'] if i!=2 else None,c['entry'].year if c['entry'] and i!=2 else None,
                  g['deadline'],g['achieved'],tr(lang,g['reason']),', '.join(f'{dataset}:{line}' for dataset,line in g['evidence']),tr(lang,g['state'])]
                 for c in selected for g in (c['goals'][i],)))
    if role!='manager':
        for field, label in (('worker','worker'),('entry','year')):
            groups = {}
            for case in cases:
                v = case[field]
                key = v.year if field=='entry' and v else v
                groups.setdefault(str(key or '—'),[]).append(case)
            tabs[tr(lang,label)] = [[tr(lang,label),tr(lang,'people'),tr(lang,'met')]] + [
                [key,len(items),rules.counts(items,0)['achieved']] for key,items in sorted(groups.items())]
        tabs['ZEMIS'] = [['ID',tr(lang,'evidence')]] + [[case['id'],','.join(map(str,case['gaps']))] for case in cases if case['gaps']]
    return tabs
