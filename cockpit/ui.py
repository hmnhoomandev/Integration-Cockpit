"""Server-rendered German, English and French interface."""
from html import escape
from urllib.parse import urlencode, quote, parse_qs, urlsplit
from itertools import chain

from . import rules
from .data import MONTHS, PHASE4_MONTH, PHASE5_MONTH
from .insights import SOURCES, FSO, AGGREGATE_INTENTS, RULE_DATES

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
 'market_unknown':('Ersten Arbeitsmarkt bestätigen','Verify primary labour-market evidence','Vérifier l’appartenance au marché primaire'),
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
 'quality_export':('Qualitätsbericht herunterladen','Download import quality report','Télécharger le rapport de qualité'),
 'invalid_demo':('Unvollständigen Testimport ausführen','Run incomplete test import','Tester un import incomplet'),
 'unexpected_column':('Zusätzliche Spalte ausserhalb des Schemas','Unexpected column outside the schema','Colonne supplémentaire hors schéma'),
 'fingerprint':('SHA-256 Prüfsumme','SHA-256 checksum','Empreinte SHA-256'),
 'import_attempt':('Letzter Importversuch','Latest import attempt','Dernière tentative d’importation'),
 'row_number':('Excel-Zeilennummer','Excel row number','Numéro de ligne Excel'),
 'result':('Ergebnis','Outcome','Résultat'),
 'scope_in':('Im Geltungsbereich','In scope','Dans le périmètre'),
 'scope_out':('Ausserhalb des Geltungsbereichs','Out of scope','Hors périmètre'),
 'scope_review':('Geltungsbereich ungeklärt','Scope unconfirmed','Périmètre non confirmé'),
 'due_status':('Friststatus','Deadline status','Statut de l’échéance'),
 'due_now':('Frist erreicht','Due by report date','Délai atteint à la date du rapport'),
 'upcoming_due':('Frist ausstehend','Deadline upcoming','Échéance à venir'),
 'due_unknown':('Frist ungeklärt','Deadline unknown','Échéance inconnue'),
 'a1_attainment':('A1 erreicht','A1 attained','A1 atteint'),
 'entry_date':('Einreisedatum','Entry date','Date d’arrivée'),
 'report_date':('Stichtag','Report date','Date du rapport'),
 'scope':('Geltungsbereich','Scope','Périmètre'),
 'official_dates':('Offizieller Eintrag','Recorded achievement','Résultat officiel enregistré'),
 'undated_proof':('Eintrag ohne Datum','Record without date','Enregistrement sans date'),
 'uncertain_proof':('Nachweis ungeklärt','Proof needs review','Justificatif à vérifier'),
 'control_totals':('Kontrollsummen A1','A1 control totals','Totaux de contrôle A1'),
 'language_policy':('Nachweissprache','Proof language','Langue du justificatif'),
 'age_reference':('Altersstichtag','Age reference','Date de référence pour l’âge'),
 'minimum_age':('Mindestalter','Minimum age','Âge minimum'),
 'employment_gap':('Beschäftigung unterbrochen','Employment intervals interrupted','Périodes d’emploi interrompues'),
 'education_unknown':('Ausbildungsbeginn ungeklärt','Education start unconfirmed','Début de formation non confirmé'),
 'household_end_unknown':('Haushaltsfrist fehlt oder widerspricht sich','Household cutoff missing or conflicting','Échéance du ménage manquante ou contradictoire'),
 'membership_unknown':('Kein bestätigter Haushaltsbestand am Stichtag','No confirmed household membership at cutoff','Composition du ménage non confirmée à la date de référence'),
 'membership_reset':('Zeitraum beginnt nach Änderung des Haushalts neu','Interval restarts after household membership changes','La période recommence après un changement de composition'),
 'period_start':('Beginn des geprüften Zeitraums','Start of evaluated interval','Début de la période examinée'),
 'baseline_end':('Exportiertes Zuständigkeitsende','Exported responsibility end','Fin de prise en charge exportée'),
 'reference_end':('Rechnerische Referenzfrist','Calculated reference cutoff','Échéance de référence calculée'),
 'transition_end':('Kandidatenfrist 2027','Candidate 2027 cutoff','Échéance envisagée pour 2027'),
 'phase5_fixture':('Testmonat für Gruppenanalyse','Group analysis test month','Mois de test des analyses de groupe'),
 'phase4_fixture':('Testmonat für Arbeit und Haushalt','Work and household test month','Mois de test travail et ménage'),
 'language_group':('Erstsprache','Mother tongue','Langue première'),
 'other_language':('Weitere Sprachen','Other languages','Autres langues'),
 'intake_sample':('Synthetisches PDF prüfen','Review synthetic PDF','Examiner le PDF synthétique'),
 'reviewed_intake':('Bestätigte Kategorie','Confirmed category','Catégorie confirmée'),
 'safe_aggregates':('Geschützte Aggregate herunterladen','Download safe aggregates','Télécharger les agrégats protégés'),
 'observed_rate':('Beobachtete Quote','Observed attainment rate','Taux d’atteinte observé'),
 'difference':('Differenz zum grössten angezeigten Segment','Difference from largest displayed group','Écart avec le plus grand groupe affiché'),
 'cutoff_year':('Fristjahr','Deadline year','Année de l’échéance'),
 'observed_to_date':('Beobachtet bis zum Stichtag · Fristjahr','Observed through the snapshot · deadline year','Observé jusqu’à la date du rapport · année de l’échéance'),
 'analysis_note':('Zellen und Komplementärzellen unterhalb des Mindestwerts werden unterdrückt. Deskriptiv, nicht kausal.','Cells and complements below the minimum are suppressed. Results describe associations.','Les cellules et compléments sous le seuil sont masqués. Résultats descriptifs.'),
 'role_worker':('Fallführung','Caseworker','Gestionnaire de dossiers'),
 'role_manager':('Leitung','Management','Direction'),
 'role_importer':('Datenimport','Import operator','Opérateur d’importation'),
 'role_judge':('Demo-Konto','Demo account','Compte de démonstration'),
 'demo_persona':('Demo-Rolle','Demo role','Rôle de démonstration'),
 'apply_role':('Rolle anzeigen','View role','Afficher le rôle'),
 'skip_main':('Zum Inhalt','Skip to content','Aller au contenu'),
 'navigation':('Hauptnavigation','Main navigation','Navigation principale'),
 'trend':('Monatsvergleich A1','Monthly A1 trend','Tendance mensuelle A1'),
 'coverage_overview':('Quellenabdeckung','Source coverage','Couverture des sources'),
 'sources_present':('Erkannte Quelldateien','Recognized source workbooks','Classeurs source reconnus'),
 'nonempty_sources':('Quellen mit Datenzeilen','Sources containing data rows','Sources contenant des lignes de données'),
 'status_filter':('Ergebnisstatus','Result status','Statut du résultat'),
 'all_statuses':('Alle Status','All statuses','Tous les statuts'),
 'reset_filters':('Filter zurücksetzen','Reset filters','Réinitialiser les filtres'),
 'queue_count':('Passende Fälle','Matching cases','Dossiers correspondants'),
 'empty_queue':('Keine Fälle für diese Filter','No cases match these filters','Aucun dossier ne correspond à ces filtres'),
 'page_number':('Seite','Page','Page'),
 'back_queue':('Zur Fallführung','Back to casework','Retour au suivi des dossiers'),
 'date_until':('Bis','Until','Jusqu’au'),
 'sheet_metadata':('Metadaten','Metadata','Métadonnées'),
 'sheet_aggregates':('Aggregate','Aggregates','Agrégats'),
 'sheet_import':('Import','Import','Importation'),
 'sheet_sources':('Quellen','Sources','Sources'),
 'sheet_issues':('Fehler','Issues','Anomalies'),
 'ci_lower':('95%-KI Untergrenze','95% CI lower','Borne inférieure IC 95 %'),
 'ci_upper':('95%-KI Obergrenze','95% CI upper','Borne supérieure IC 95 %'),
 'confidence_interval':('95%-Konfidenzintervall','95% confidence interval','Intervalle de confiance à 95 %'),
 'case_identifier':('Fallkennung','Case ID','Identifiant du dossier'),
 'difference_short':('Differenz','Difference','Écart'),
 'baseline':('Basis','Baseline','Référence'),
 'candidate':('Szenario','Scenario','Scénario'),
 'verified_attainment':('Fristgerecht und bestätigt','On time and corroborated','Dans les délais et corroboré'),
 'uncorroborated':('Fristgerecht ohne Bestätigung','On time without corroboration','Dans les délais sans corroboration'),
 'scenario_note':('Unverbindlicher Vergleich mit exportierter Frist. Keine Änderung am Import.','Illustrative comparison against the exported cutoff. The snapshot stays intact.','Comparaison indicative avec l’échéance exportée. L’instantané reste intact.'),
 'payment_title':('Illustrative Abgeltung','Illustrative payments','Paiements indicatifs'),
 'payment_note':('Nur übereinstimmende Nachweise und offizielle Datumsangaben werden bepreist. Tarife sind Annahmen.','Only matching evidence and official dates are priced. Rates are assumptions.','Seules les preuves et dates officielles concordantes sont chiffrées. Les tarifs sont hypothétiques.'),
 'rate_chf':('Ansatz in CHF','Rate in CHF','Tarif en CHF'),
 'amount_chf':('Betrag in CHF','Amount in CHF','Montant en CHF'),
 'due_soon':('Frist in den nächsten 30 Tagen','Due in the next 30 days','Échéance dans les 30 jours'),
 'unassigned':('Nicht zugewiesen','Unassigned','Non attribué'),
 'zemis_dates_unknown':('Beschäftigungsdaten ungeklärt','Employment dates need review','Dates d’emploi à vérifier'),
 'zemis_no_overlap':('Kein zeitlich passender Erwerbseintrag','No overlapping employment entry','Aucun emploi sur la même période'),
 'zemis_employer_unknown':('Arbeitgeber nicht sicher abgeglichen','Employer match unconfirmed','Correspondance employeur non confirmée'),
 'month':('Monat','Month','Mois'),
 'count':('Anzahl','Count','Nombre'),
 'validation_months':('Modellauswahl (Monate)','Model selection (months)','Sélection du modèle (mois)'),
 'gate_months':('Validierungsschranke (Monate)','Validation gate (months)','Seuil de validation (mois)'),
 'gate_error':('Validierungsschranke · MAE','Validation gate · MAE','Seuil de validation · MAE'),
 'heldout_error':('Separater Test · MAE','Held-out test · MAE','Test séparé · MAE'),
 'horizon':('Prognosehorizont','Forecast horizon','Horizon de prévision'),
 'interval_coverage':('Intervallabdeckung im Test','Held-out interval coverage','Couverture de l’intervalle en test'),
 'model_last':('Letzter Monatswert','Last observation','Dernière observation'),
 'model_seasonal':('Vorjahr','Seasonal baseline','Référence saisonnière'),
 'model_trend':('Linearer Trend','Linear trend','Tendance linéaire'),
 'privacy_denied':('Anfrage ausserhalb des erlaubten Schemas','Request outside the allowed schema','Requête hors schéma autorisé'),
 'authority':('Herausgeber','Issuing authority','Autorité émettrice'),
 'published':('Dokument verfügbar ab','Document available from','Document disponible dès le'),
 'effective':('Inkrafttreten laut Quelle','Effective date stated by source','Date d’effet indiquée par la source'),
 'date_unspecified':('In der Challenge nicht angegeben','Unspecified in the challenge','Non indiquée dans le défi'),
 'upcoming_rule':('Zum gewählten Datum liegt die Änderung in der Zukunft.','The change is still in the future on the selected date.','Le changement est futur à la date sélectionnée.'),
 'rule_conflict':('Gleichrangige Quellen widersprechen sich. Fachprüfung erforderlich.','Sources with equal authority disagree. Expert review is required.','Des sources de même autorité se contredisent. Vérification requise.'),
 'rule_insufficient':('Keine geprüfte Quelle für das gewählte Datum gefunden.','No reviewed source applies to this selection.','Aucune source vérifiée ne correspond à cette sélection.'),
 'context_link':('Öffentlicher Kontext','Public context','Contexte public'),
 'rule_date':('Quellenstichtag','Source lookup date','Date de consultation des sources'),
 'entry_cohort':('Niedrigste beobachtete Quote','Lowest observed rate','Taux observé le plus faible'),
 'strongest_cohort':('Höchste beobachtete Quote','Highest observed rate','Taux observé le plus élevé'),
 'monthly_change':('Was änderte sich zwischen den Monaten?','What changed between months?','Quel changement entre les mois ?'),
 'monthly_note':('Die Änderung folgt aus den Monatszählungen. Die Daten erklären keine Ursachen.','This difference comes from the monthly counts. The data do not establish causes.','L’écart provient des comptages mensuels. Les données ne permettent pas d’établir une cause.'),
 'local_release':('Freigabe bleibt in der Anwendung. Keine Modellanfrage.','The released fields stay in the application. No model request is made.','Les champs autorisés restent dans l’application. Aucun appel à un modèle.'),
 'aggregate_role':('Aggregierte Antworten für Leitung und Demo-Konto','Aggregate answers for management and the demo account','Réponses agrégées pour la direction et le compte de démonstration'),
 'missing_source':('Pflichtdatei fehlt','Required workbook is missing','Classeur obligatoire manquant'),
 'unrecognized_or_invalid_workbook':('Datei ungültig oder doppelt','Invalid or duplicate workbook','Classeur invalide ou en double'),
 'invalid_worksheet_data':('Ungültige Tabelleninhalte','Invalid worksheet content','Contenu de feuille invalide'),
 'numeric_identifier':('Kennung als Textformat erforderlich','Identifier must be stored as text','L’identifiant doit être enregistré comme texte'),
 'invalid_date':('Ungültiges Datum','Invalid date','Date invalide'),
 'date_range':('Enddatum liegt vor dem Start','End date precedes start date','La date de fin précède le début'),
 'duplicate_row':('Zeile ist doppelt','Duplicate row','Ligne en double'),
 'invalid_or_conflicting_client_key':('Personenschlüssel fehlt oder ist widersprüchlich','Missing or conflicting personal key','Clé personnelle manquante ou contradictoire'),
 'unresolved_household':('Haushalt nicht zugeordnet','Household link unresolved','Lien avec le ménage non résolu'),
 'unresolved_or_conflicting_person':('Personenzuordnung ungeklärt','Unresolved or conflicting person link','Lien avec la personne non résolu ou contradictoire'),
 'conflicting_current_status':('Aktuelle Status widersprüchlich','Conflicting current statuses','Statuts actuels contradictoires'),
 'invalid_value':('Ungültiger Wert','Invalid value','Valeur invalide'),
 'empty_clients':('Personentabelle leer','Client table is empty','Table des personnes vide'),
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
 'assumptions':('Ausbildungsbeginn zählt; keine Zusammenrechnung paralleler Stellen; Unterstützungsabdeckung nur für synthetische Daten als vollständig behandelt.','Enrolment qualifies; concurrent jobs are evaluated separately; complete assistance coverage is assumed for synthetic data only.','Début de formation retenu, emplois simultanés évalués séparément et couverture complète supposée pour les seules données synthétiques.'),
 'review_save':('Kategorie bestätigen','Confirm category','Confirmer la catégorie'),
 'pdf_review':('PDF lokal auswerten','Review PDF locally','Examiner le PDF localement'),
 'ocr_review':('OCR-Vorschlag. ZEMIS und Kategorie am Original prüfen.','OCR suggestion. Check ZEMIS and the category against the original.','Suggestion OCR. Vérifier le ZEMIS et la catégorie sur l’original.'),
 'manual':('Manuelle Prüfung erforderlich','Manual review required','Vérification manuelle nécessaire'),
 'category':('Kategorie','Category','Catégorie'),
 'scenario2027':('Szenario 2027','2027 scenario','Scénario 2027'),
 'tariff':('Illustrative Abgeltung pro fristgerechtes A1','Illustrative payment per on-time A1','Montant illustratif par A1 dans les délais'),
 'synthetic_only':('Nur Testdaten','Synthetic data only','Données synthétiques uniquement'),
 'schooling':('Schulbildung','Prior schooling','Scolarité antérieure'),
 'course':('Kursteilnahme','Course participation','Participation à un cours'),
 'scheduling':('Betreuungszeiten','Childcare scheduling','Horaires de garde'),
 'housing':('Wohnstabilität','Housing stability','Stabilité du logement'),
 'explorer':('Faktorenanalyse','Factor explorer','Exploration des facteurs'),
 'age':('Alter','Age','Âge'),
 'course_yes':('Sprachkurs erfasst','Language course recorded','Cours de langue enregistré'),
 'course_none':('Kein Sprachkurs erfasst','No language course recorded','Aucun cours de langue enregistré'),
 'observation':('Nur Kohorten mit abgelaufener A1-Frist','Cohorts with completed A1 follow-up','Cohortes dont le suivi A1 est terminé'),
 'missing':('Fehlende Angaben','Missing information','Données manquantes'),
 'timeline':('Verlauf','Timeline','Historique'),
 'caseload':('Fallbelastung nach Zuständigkeit','Caseload by assignment','Charge de travail par affectation'),
 'compare':('Wirkung auf Zuständigkeitsende','Change in responsibility end dates','Effet sur la fin de prise en charge'),
 'quality_note':('Abgleich von Zeiträumen; Unstimmigkeiten müssen geprüft werden.','Date overlap comparison; discrepancies require review.','Comparaison des périodes ; les écarts doivent être vérifiés.'),
 'employment_status':('Erwerbsstatus','Employment category','Catégorie d’emploi'),
 'change':('Stichtag vergleichen','Compare snapshots','Comparer les instantanés'),
 'aggregate_upload':('Monatszahlen hochladen','Upload monthly aggregate counts','Importer des agrégats mensuels'),
 'aggregate_reset':('Importierte Reihe entfernen','Remove uploaded series','Supprimer la série importée'),
 'aggregate_local':('Lokal importierte Monatsreihe','Locally uploaded monthly series','Série mensuelle importée localement'),
 'aggregate_help':('CSV mit month,count und mindestens 42 aufeinanderfolgenden Monaten. Nur aggregierte Daten.','CSV with month,count and at least 42 consecutive months. Aggregate data only.','CSV avec month,count et au moins 42 mois consécutifs. Données agrégées uniquement.'),
 'source_limit':('Lehrpersonen- und Betreuungsverläufe liegen in den Exporten nicht als verknüpfbare Zeitreihen vor.','The exports lack linkable teacher and childcare histories.','Les exports ne contiennent pas d’historique chaînable des enseignants ou de la garde.'),


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


def layout(lang,active,body,account=None,csrf='',snapshot=None,demo_switch=False,view_path=''):
    menus = ['overview','queue','reports','ai','forecast','intake']
    if account:
        if account['role']=='worker':
            menus.remove('forecast')
        if account['role']=='manager':
            menus = [m for m in menus if m not in ('queue','intake')]
        if account['role']=='importer':
            menus = ['reports','intake','ai']
    nav = ''.join(f'<a href="/{key}" {"aria-current=page" if key==active or key=="queue" and active=="case" else ""}>{text(lang,key)}</a>' for key in menus) if account else ''
    target = urlsplit(view_path or '/'+active)
    parameters = parse_qs(target.query)
    filters = {k:parameters[k][0] for k in ('q','state','page','goal','factor','topic','intent','asof') if k in parameters}
    language = ''.join(f'<a lang="{locale}" href="{href(f'/language/{locale}', view=target.path, **filters)}" {"aria-current=page" if i==lang else ""}>{locale[:2].upper()}</a>'
                       for i,locale in enumerate(LOCALES))
    date = f'<span class="snapshot">{text(lang,"snapshot")} <strong>{esc(snapshot["asof"])}</strong></span>' if snapshot else ''
    logout = post('/logout',csrf,action(lang,'logout')) if account else ''
    persona = ''
    if demo_switch:
        opts = ''.join(f'<option value="{key}" {"selected" if key==account["role"] else ""}>{text(lang,"role_"+key)}</option>'
                       for key in ('judge','worker','manager','importer'))
        persona = post('/demo-role',csrf,f'<label>{text(lang,"demo_persona")} <select name="role">{opts}</select></label>'+action(lang,'apply_role'))
    role_label = f'<span class="role-label">{text(lang,"role_"+account["role"])}</span>' if account else ''
    frame = f'<aside><a class="brand" href="/"><span aria-hidden="true">✳</span><div>Integrations-Cockpit<small>Bern</small></div></a><nav aria-label="{text(lang,"navigation")}">{nav}</nav><div class="aside-bottom">{role_label}{persona}</div></aside>' if account else ''
    mode = 'dashboard' if account else 'signin'
    return f'''<!doctype html><html lang="{LOCALES[lang]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{text(lang,active)} · Integrations-Cockpit Bern</title><link rel="stylesheet" href="/static/app.css"></head>
<body class="{mode}"><a class="skip-link" href="#main">{text(lang,"skip_main")}</a>{frame}<div class="workspace"><header>{date}<div class="header-actions"><div class="languages">{language}</div>{logout}</div></header>
<main id="main" tabindex="-1">{body}<footer class="photo-credit">{'<a href="https://commons.wikimedia.org/wiki/File:Bern_Altstadt_von_Rosengarten_20211007.jpg">Bern · Daniel Kraft</a> · <a href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0</a>' if active in ('overview','login') else ''}</footer></main></div></body></html>'''


def overview(lang,snapshot,cases,management,dimension='year',intake_categories=None,goal_index=0,trend=()):
    s = rules.counts(cases,0)
    metrics = (('people',len(cases)),('homes',len({c['home'] for c in cases})),('met',s['achieved']),
               ('follow',sum(s[key] for key in ('risk','overdue','review'))))
    if management and snapshot['source']!='synthetic':
        metrics = tuple((key,'—') for key,_ in metrics)
    kpis = ''.join(f'<article class="kpi"><span>{text(lang,k)}</span><strong>{v}</strong></article>' for k,v in metrics)
    goals = []
    for i,key in enumerate(('a1','work','household')):
        totals = rules.counts(cases,i)
        statuses = [(state,count) for state,count in totals.most_common() if snapshot['source']=='synthetic' or not management]
        rows = ''.join(f'<li>{badge(lang,state)}<strong>{count}</strong></li>' for state,count in statuses)
        goals.append(f'<article class="panel"><h3>{text(lang,key)}</h3><ul class="breakdown">{rows}</ul></article>')
    factor_panel = ''
    if snapshot['source']=='synthetic':
        from datetime import date
        breakdown,coverage,public = rules.analysis(cases,date.fromisoformat(snapshot['asof']),dimension,intake_categories,goal_index)
        choices = ''.join(f'<a class="chip" href="/overview?factor={k}" {"aria-current=page" if k==dimension else ""}>{text(lang,k)}</a>'
                          for k in rules.FACTOR_DIMENSIONS) if goal_index==0 else ''
        goal_choices = ''.join(f'<a class="chip" href="/overview?goal={i}" {"aria-current=page" if i==goal_index else ""}>{text(lang,k)}</a>'
                               for i,k in enumerate(('a1','work','household')))
        comparator = max(public,key=lambda row:row[1],default=None)
        baseline = comparator[3]/comparator[1] if comparator else None
        rendered = table([tr(lang,'category'),'n',tr(lang,'observed_rate'),tr(lang,'met'),tr(lang,'confidence_interval'),tr(lang,'difference')],
          ((text(lang,label),esc(n) if n else text(lang,'suppressed'), f'{observed/n:.1%}' if n else '—',
            f'{k/n:.1%}' if n else '—',f'{band[0]:.0%}–{band[1]:.0%}' if band else '—',
            f'{(k/n-baseline)*100:+.1f} pp' if n else '—') for label,n,observed,k,band in breakdown))
        window = text(lang,'observation' if goal_index==0 else 'observed_to_date')
        upcoming = esc(coverage['upcoming']) if coverage.get('upcoming') is not None else text(lang,'suppressed')
        missing = esc(coverage['missing']) if coverage.get('missing') is not None else text(lang,'suppressed')
        aggregates = href('/analysis-export',factor=dimension,goal=goal_index)
        workers = {}
        for c in cases:
            workers.setdefault(c['worker'],[]).append(c)
        now = date.fromisoformat(snapshot['asof'])
        def workload(items):
            due = sum(any(g['deadline'] and 0<=(g['deadline']-now).days<=30 and
                          g['state'] in ('ontrack','risk','review') for g in c['goals']) for c in items)
            review = sum(any(g['state']=='review' for g in c['goals']) for c in items)
            return len(items),len({c['home'] for c in items}),due,review,sum(bool(c['gaps']) for c in items)
        workers.setdefault('–',[])
        workload_rows = []
        for key,items in sorted(workers.items()):
            if len(items)>=rules.MIN_GROUP or key=='–':
                values = (text(lang,'suppressed'),)*5 if 0<len(items)<rules.MIN_GROUP else tuple(esc(n) for n in workload(items))
                workload_rows.append((text(lang,'unassigned') if key=='–' else esc(key),*values))
        caseload = table([tr(lang,k) for k in ('worker','people','homes','due_soon','review','quality')],workload_rows)
        factor_panel = f'<section class="panel"><h2>{text(lang,"explorer")}</h2><p>{window} · {esc(snapshot["asof"])} · {text(lang,"upcoming_due")} {upcoming} · {text(lang,"missing")} {missing}</p><div class="chips">{goal_choices}</div><div class="chips">{choices}</div>{rendered}<p>{text(lang,"analysis_note")}</p><p>{text(lang,"source_limit")}</p><a class="button" href="{aggregates}">{text(lang,"safe_aggregates")}</a></section><section class="panel"><h2>{text(lang,"caseload")}</h2>{caseload}<p>{text(lang,"quality_note")}</p></section>'
    import json
    sources = json.loads(snapshot['inspected'])
    coverage_card = f'<section class="panel"><h2>{text(lang,"coverage_overview")}</h2><dl><dt>{text(lang,"sources_present")}</dt><dd>{len(sources)}</dd><dt>{text(lang,"nonempty_sources")}</dt><dd>{sum(n>0 for n in sources.values())}</dd></dl><a href="/reports">{text(lang,"reports")}</a></section>'
    trend_card = ''
    if trend:
        rows = ((esc(d),esc(n),esc(k),f'{k/n:.1%}' if n else text(lang,'suppressed')) for d,n,k in trend)
        trend_card = f'<section class="panel"><h2>{text(lang,"trend")}</h2>'+table(
            [tr(lang,'snapshot'),tr(lang,'scope_in'),tr(lang,'met'),'%'],rows)+'</section>'
    return f'''<section class="hero"><img class="bern-image" src="/static/bern.jpg" alt=""><div class="hero-copy"><p class="eyebrow">{text(lang,'demo' if snapshot['source']=='synthetic' else 'local')}</p>
{heading(lang,'overview',text(lang,'lead'))}</div></section>
<div class="kpis">{kpis}</div><div class="two">{coverage_card}{trend_card}</div><h2>{text(lang,'goals')}</h2><div class="three">{''.join(goals)}</div>
{factor_panel}'''


def analysis_export(lang,snapshot,cases,dimension,intake_categories,goal_index):
    from datetime import date
    asof = date.fromisoformat(snapshot['asof'])
    rows,coverage,_ = rules.analysis(cases,asof,dimension,intake_categories,goal_index)
    return {
        tr(lang,'sheet_metadata'): [[tr(lang,'snapshot'),asof],[tr(lang,'source'),tr(lang,'demo')],
                     [tr(lang,'goals'),tr(lang,('a1','work','household')[goal_index])],
                     [tr(lang,'category'),tr(lang,dimension if goal_index==0 else 'cutoff_year')],
                     [tr(lang,'upcoming_due'),coverage.get('upcoming')],[tr(lang,'missing'),coverage.get('missing')]],
        tr(lang,'sheet_aggregates'): [[tr(lang,'category'),'n',tr(lang,'a1_attainment') if goal_index==0 else tr(lang,'attained'),
                       tr(lang,'met'),tr(lang,'ci_lower'),tr(lang,'ci_upper')]] +
                      [[tr(lang,label),n,observed,k,*(band or (None,None))] for label,n,observed,k,band in rows],
    }


def queue(lang,cases,query,page,filter_state):
    limits = {'overdue':0,'risk':1,'review':2,'ontrack':3,'late':4,'achieved':5,'na':6}
    cases = [c for c in cases if query.casefold() in c['id'].casefold()
             and (not filter_state or c['goals'][0]['state']==filter_state)]
    cases.sort(key=lambda c:(limits[c['goals'][0]['state']],str(c['goals'][0]['deadline'] or '9999'),c['id']))
    offset = (page-1)*20
    options = ''.join(f'<option value="{key}" {"selected" if key==filter_state else ""}>{text(lang,key)}</option>' for key in limits)
    form = f'''<form class="inline" action="/queue"><label>{text(lang,'search')} <input name="q" value="{esc(query)}"></label>
<label>{text(lang,'status_filter')} · {text(lang,'a1')} <select name="state"><option value="">{text(lang,'all_statuses')}</option>{options}</select></label>{action(lang,'search')}<a class="chip" href="/queue">{text(lang,'reset_filters')}</a></form>'''
    rows = ((f'<a class="case-link" href="/case/{quote(c["id"],safe="")}">{esc(c["id"])}</a>',
             *(badge(lang,g['state']) for g in c['goals']),esc(c['goals'][0]['deadline']),text(lang,c['goals'][0]['reason']))
            for c in cases[offset:offset+20])
    pagination = '<div class="pagination">'
    if page>1:
        pagination += f'<a href="{href("/queue",q=query,state=filter_state,page=page-1)}">{text(lang,"previous")}</a>'
    if offset+20<len(cases):
        pagination += f'<a href="{href("/queue",q=query,state=filter_state,page=page+1)}">{text(lang,"next")}</a>'
    count = f'<p class="result-count">{text(lang,"queue_count")} · {len(cases)} · {text(lang,"page_number")} {page}</p>'
    if not cases[offset:offset+20]:
        return heading(lang,'queue')+form+count+f'<section class="panel"><p>{text(lang,"empty_queue")}</p></section>'+pagination+'</div>'
    return heading(lang,'queue')+form+count+table([tr(lang,'case_identifier'),*(tr(lang,k) for k in ('a1','work','household','deadline','reason'))],rows)+pagination+'</div>'


def detail(lang,case):
    sections = []
    for key,g in zip(('a1','work','household'),case['goals']):
        ev = ', '.join(f'{esc(k)} #{line}' for k,line in g['evidence']) or '—'
        rows = [(tr(lang,'deadline'),g['deadline']),(tr(lang,'attained'),g['achieved']),(tr(lang,'scenario'),g['earliest'])]
        official = ', '.join(map(str,g.get('official_dates',())))
        if g.get('official_undated'):
            official = (official+' · ' if official else '')+tr(lang,'undated_proof')
        rows.append((tr(lang,'official_dates'),official or None))
        if key=='a1':
            due_key = {True:'due_now',False:'upcoming_due',None:'due_unknown'}[g.get('due')]
            due = tr(lang,due_key) if g['scope']=='scope_in' else None
            rows.extend([(tr(lang,'scope'),tr(lang,g['scope'])),(tr(lang,'entry_date'),case['entry']),
                         (tr(lang,'due_status'),due)])
        elif key=='work':
            rows.extend((tr(lang,label),case[field]) for label,field in (
                ('baseline_end','end'),('reference_end','reference_end'),('transition_end','transition_end')))
        else:
            rows.append((tr(lang,'period_start'),g.get('period_start')))
        facts = ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k,v in rows)
        sections.append(f'<section class="panel"><h2>{text(lang,key)}</h2>{badge(lang,g["state"])}<p>{text(lang,g["reason"])}</p><dl>{facts}<dt>{text(lang,"evidence")}</dt><dd>{ev}</dd></dl></section>')
    timeline = []
    for dataset, label, start, end, fact in (
        ('work','work','Von','Bis','Erwerbsstatus'),('education','education','Start','Abschluss','Art'),
        ('housing','housing','Unterbringung Von','Unterbringung Bis','Unterbringung Art'),
        ('status','case','Verfahrensstand Gültig ab','Verfahrensstand Gültig bis','Verfahrensstand')):
        for record in case['tables'][dataset][:20]:
            timeline.append((record.get(start) or '',record.get(end),label,record.get(fact)))
    rows = table([tr(lang,'source'),tr(lang,'category'),tr(lang,'deadline'),tr(lang,'date_until')],
        ((text(lang,label),esc(value),esc(a),esc(b)) for a,b,label,value in sorted(timeline,key=lambda row:row[0],reverse=True)))
    quality = ''
    if case['zemis_findings']:
        findings = table(['ZEMIS',tr(lang,'result'),tr(lang,'evidence')],
                         ((esc(line),text(lang,reason),esc(', '.join(map(str,rows))))
                          for line,reason,rows in case['zemis_findings']))
        quality = f'<section class="panel"><h2>{text(lang,"quality")}</h2>{findings}</section>'
    return heading(lang,'case',esc(case['id']))+f'<a class="chip back-link" href="/queue">{text(lang,"back_queue")}</a><div class="three">'+''.join(sections)+f'</div><section class="panel"><h2>{text(lang,"timeline")}</h2>{rows}</section>{quality}'



def reports(lang,snapshot,history,role,csrf,hosted,notice='',issues=(),manifest=()):
    report = f'<a class="button" href="/export">{text(lang,"export")}</a>' if role!='importer' and snapshot else ''
    import_controls = ''
    if role in ('judge','importer'):
        button = action(lang,'synthetic_load')
        options = ''.join(f'<option>{d}</option>' for d in MONTHS)
        exercise = options+f'<option value="{PHASE4_MONTH}">{PHASE4_MONTH} · {text(lang,"phase4_fixture")}</option>'
        exercise += f'<option value="{PHASE5_MONTH}">{PHASE5_MONTH} · {text(lang,"phase5_fixture")}</option>'
        import_controls = post('/seed',csrf,f'<label>{text(lang,"snapshot")} <select name="date">{exercise}</select></label>{button}')
        import_controls += post('/seed-invalid',csrf,
            f'<label>{text(lang,"snapshot")} <select name="date">{options}</select></label>'+action(lang,'invalid_demo'))
        report += f'<a class="button" href="/quality">{text(lang,"quality_export")}</a>'
        if not hosted:
            import_controls += post('/import',csrf,
                f'<label>{text(lang,"snapshot")} <input name="date" type="date" required></label>'
                f'<label>Excel <input name="workbooks" type="file" accept=".xlsx" multiple required></label>{action(lang,"import")}',True)
    current = ''
    if snapshot:
        import json
        counts = json.loads(snapshot['inspected'])
        current = table([tr(lang,'source'),tr(lang,'rows')],((esc(k),esc(n)) for k,n in counts.items()))
        if manifest:
            records = table([tr(lang,'source'),tr(lang,'fingerprint')],
                            ((esc(r['dataset']),'<code>'+esc(r['sha256'])+'</code>') for r in manifest))
            current += f'<details><summary>{text(lang,"fingerprint")}</summary>{records}</details>'
    choices = ''.join(f'<option value="{r["id"]}">{esc(r["asof"])} · {text(lang,"demo" if r["source"]=="synthetic" else "local")}</option>' for r in history)
    history_form = post('/snapshot',csrf,f'<label>{text(lang,"snapshot")} <select name="id">{choices}</select></label>{action(lang,"choose")}') if choices else ''
    errors = ''.join(f'<li>{esc(k)} · #{i} · {text(lang,r)}</li>' for k,i,r in issues)
    feedback = f'<div class="feedback" role="status">{text(lang,notice)}<ul>{errors}</ul></div>' if notice else ''
    return heading(lang,'reports')+feedback+f'''
<section class="panel actions">{history_form}{import_controls}{report}</section>
<div class="two"><section class="panel"><h2>{text(lang,'coverage')}</h2>{current}</section>
<section class="panel"><h2>{text(lang,'policy')}</h2><p class="mono">{rules.VERSION}</p><p>{text(lang,'assumptions')}</p><p>{text(lang,'language_policy')} · {esc(rules.A1_POLICY['language'])}<br>{text(lang,'minimum_age')} · {rules.A1_POLICY['minimum_age']}<br>{text(lang,'age_reference')} · {text(lang,rules.A1_POLICY['age_reference'])}</p></section></div>'''


def quality_export(lang,snapshot,diagnostic,issues,counts,manifest):
    status = {'accepted':'uploaded','repeated':'repeated','rejected':'rejected'}
    hashes = {r['dataset']:r['sha256'] for r in manifest}
    return {
        tr(lang,'sheet_import'): [[tr(lang,'snapshot'),snapshot['asof'] if snapshot else None],
                   [tr(lang,'source'),tr(lang,'demo' if snapshot['source']=='synthetic' else 'local') if snapshot else None],
                   [tr(lang,'import_attempt'),diagnostic['report_date'] if diagnostic else None],
                   [tr(lang,'result'),tr(lang,status[diagnostic['outcome']]) if diagnostic else None]],
        tr(lang,'sheet_sources'): [[tr(lang,'source'),tr(lang,'rows'),tr(lang,'fingerprint')]] +
                   [[k,n,hashes.get(k)] for k,n in counts.items()],
        tr(lang,'sheet_issues'): [[tr(lang,'source'),tr(lang,'row_number'),tr(lang,'result'),'Code']] +
                  [[key,line,tr(lang,reason),reason] for key,line,reason in issues],
    }


def assistant(lang,topic,result,aggregate,intent='entry_cohort',asof=RULE_DATES[0]):
    topics = ''.join(f'<a class="chip" href="{href("/ai",topic=k,intent=intent,asof=asof)}" {"aria-current=page" if k==topic else ""}>{text(lang,k)}</a>' for k in SOURCES)
    dates = ''.join(f'<option {"selected" if d==asof else ""}>{esc(d)}</option>' for d in RULE_DATES)
    date_picker = f'<form action="/ai"><input type="hidden" name="topic" value="{esc(topic)}"><input type="hidden" name="intent" value="{esc(intent)}"><label>{text(lang,"rule_date")} <select name="asof">{dates}</select></label>{action(lang,"choose")}</form>'
    if result['mode']=='retrieval_only':
        fields = [('authority',result['owner']),('policy',result['version']),('published',result['available_from']),
                  ('effective',result['effective_from'] or tr(lang,'date_unspecified'))]
        metadata = ''.join(f'<dt>{text(lang,k)}</dt><dd>{esc(v)}</dd>' for k,v in fields)
        answer = f'<p>{esc(result["text"])}</p><p class="source">{esc(result["source"])} · <a href="{esc(result["context_url"])}">{text(lang,"context_link")} · {esc(result["section"])}</a></p><dl>{metadata}</dl>'
        if result['upcoming']:
            answer += f'<p>{text(lang,"upcoming_rule")}</p>'
    elif result['mode']=='conflict':
        answer = f'<p>{text(lang,"rule_conflict")}</p><p>{esc(" · ".join(result["citations"]))}</p>'
    else:
        answer = f'<p>{text(lang,"rule_insufficient")}</p>'
    if aggregate is None:
        aggregate_body = f'<p>{text(lang,"aggregate_role")}</p>'
    else:
        intents = ''.join(f'<a class="chip" href="{href("/ai",topic=topic,intent=k,asof=asof)}" {"aria-current=page" if k==intent else ""}>{text(lang,k)}</a>' for k in AGGREGATE_INTENTS)
        if 'points' in aggregate:
            points = table([tr(lang,'snapshot'),tr(lang,'scope_in'),tr(lang,'met')],
                           ((esc(d),esc(n),esc(k)) for d,n,k in aggregate['points']))
            presentation = f'<p>{text(lang,"difference_short")} · {aggregate["delta"]:+d}</p>{points}<p>{text(lang,"monthly_note")}</p>'
        elif 'groups' in aggregate:
            groups = table([tr(lang,'year'),tr(lang,'eligible'),tr(lang,'met')],
                           ((esc(y),esc(n),esc(k)) for y,n,k in aggregate['groups']))
            presentation = f'<p>{text(lang,"observation")} · {esc(aggregate["snapshot"])}</p>{groups}'
        else:
            presentation = f'<p>{text(lang,"suppressed")} · {esc(aggregate["snapshot"])}</p>'
        aggregate_body = f'<div class="chips">{intents}</div>{presentation}<p>{text(lang,"group_note")}</p>'
    return heading(lang,'ai',text(lang,'retrieval'))+f'''
<div class="chips">{topics}</div><section class="panel reading"><h2>{text(lang,topic)}</h2>{date_picker}{answer}</section>
<div class="two"><section class="panel"><h2>{text(lang,'privacy')}</h2><dl>
<dt>{text(lang,'before')}</dt><dd><code>DEMO-00001 · 08.04.1987 · A1</code></dd>
<dt>{text(lang,'after')}</dt><dd><code>{{"topic": "{esc(topic)}", "locale": "{LOCALES[lang]}", "asof": "{esc(asof)}"}}</code></dd></dl><p>{text(lang,'local_release')}</p></section>
<section class="panel"><h2>{text(lang,'explorer')}</h2>{aggregate_body}</section></div>'''


def forecast(lang,report,tariffs,cases,series=None,can_upload=False,csrf='',candidate=None):
    values = report['values']
    top = max(values+[report['hi']])
    bars = ''.join(f'<meter min="0" max="{top}" value="{v}" aria-label="{i+1}: {v}">{v}</meter>'
                   for i,v in enumerate(values[-24:],len(values)-23))
    from datetime import date
    dates = [row[0] for row in series] if series else [rules.months(date(2022,1,1),i).strftime('%Y-%m') for i in range(len(values))]
    observations = table([tr(lang,'month'),tr(lang,'count')],((esc(month),esc(v)) for month,v in zip(dates,values)))
    forecast_month = rules.months(date.fromisoformat(dates[-1]+'-01'),report['horizon']).strftime('%Y-%m')
    checks = table([tr(lang,'forecast'),tr(lang,'gate_error'),tr(lang,'heldout_error')],
                   ((text(lang,'model_'+k),esc(report['gate_mae'][k]),esc(v)) for k,v in report['mae'].items()))
    status = f'{text(lang,"model_"+report["model"])} · {text(lang,"heldout")} {report["heldout"]} · {text(lang,"interval_coverage")} {report["coverage"]:.0%}'
    series_meta = f'{esc(dates[0])} → {esc(dates[-1])} · {len(values)} · '+text(lang,'aggregate_local' if series else 'demo')
    scenario = ''
    if candidate is not None:
        changed = sum(a['end']!=b['effective_end'] for a,b in zip(cases,candidate,strict=True))
        scenario_rows = []
        for i,key in enumerate(('a1','work','household')):
            baseline,before = rules.counts(cases,i),rules.counts(candidate,i)
            for state in ('achieved','review','overdue','ontrack','risk'):
                a,b = baseline[state],before[state]
                scenario_rows.append((text(lang,key),text(lang,'met' if state=='achieved' and i==0 else state),esc(a),esc(b),f'{b-a:+d}'))
        comparison = table([tr(lang,k) for k in ('goals','result','baseline','candidate','difference_short')],scenario_rows)
        payment_rows = []
        for key,tariff,(verified,unconfirmed,review) in zip(('a1','work','household'),tariffs,rules.payments(cases),strict=True):
            payment_rows.append((text(lang,key),esc(verified),esc(unconfirmed),esc(review),
                                 f'<input type="number" aria-label="{text(lang,key)} · {text(lang,"rate_chf")}" name="rate_{key}" min="0" max="100000" value="{tariff}">',
                                 f'CHF {verified*tariff:,}'))
        pricing = table([tr(lang,k) for k in ('goals','verified_attainment','uncorroborated','review','rate_chf','amount_chf')],payment_rows)
        scenario = f'<section class="panel"><h2>{text(lang,"scenario2027")}</h2><p>VA / F-FL · {esc(rules.RESPONSIBILITY_POLICY["version"])} · {changed}/{len(cases)}</p><p>{text(lang,"scenario_note")}</p>{comparison}</section><section class="panel"><h2>{text(lang,"payment_title")}</h2><p>{text(lang,"payment_note")}</p><form class="pricing" action="/forecast">{pricing}{action(lang,"choose")}</form></section>'
    controls = ''
    if can_upload:
        controls = '<section class="panel"><p>'+text(lang,'aggregate_help')+'</p>'+post('/forecast-upload',csrf,
            '<label>CSV <input type="file" name="series" accept=".csv,text/csv" required></label>'+action(lang,'aggregate_upload'),True)
        if series:
            controls += post('/forecast-reset',csrf,action(lang,'aggregate_reset'))
        controls += '</section>'
    return heading(lang,'forecast',text(lang,'aggregate_local' if series else 'model'))+f'''
<div class="two"><section class="panel reading"><h2>{text(lang,'interval')}</h2><strong class="forecast-value">{report['est']} <small>{report['lo']}–{report['hi']}</small></strong>
<p>{status}</p><div class="series" aria-hidden="true">{bars}</div><details><summary>{text(lang,'data_card')}</summary>
<p>{series_meta}</p>{observations}</details><p>{text(lang,'horizon')} · {forecast_month}</p></section>
<section class="panel"><h2>MAE</h2><p>{text(lang,'validation_months')} · {report['validation_months']}<br>{text(lang,'gate_months')} · {report['gate_months']}</p>{checks}</section></div>
<section class="panel"><h2>{text(lang,'public')}</h2><p>{text(lang,'public_note')}</p><a href="{FSO}">{text(lang,'source')} · BFS / FSO</a></section>{scenario}{controls}'''


def login(lang,csrf,error=''):
    return '<section class="login-hero"><img class="bern-image" src="/static/bern.jpg" alt=""><div><p class="eyebrow">'+text(lang,'demo')+'</p><h1>Integrations-<br>Cockpit Bern</h1><p>'+text(lang,'lead')+'</p></div></section><section class="login-card">'+heading(lang,'login')+(
        f'<p class="feedback" role="alert">{text(lang,error)}</p>' if error else '')+post('/login',csrf,
        f'<label>{text(lang,"username")}<input name="username" autocomplete="username" required></label>'
        f'<label>{text(lang,"password")}<input name="password" type="password" autocomplete="current-password" required></label>'
        +action(lang,'login'))+'</section>'


def export(lang,snapshot,cases,role):
    keys = ('a1','work','household')
    source = tr(lang,'demo' if snapshot['source']=='synthetic' else 'local')
    import json
    tabs = {tr(lang,'data_card'):[[tr(lang,'snapshot'),snapshot['asof']],[tr(lang,'source'),source],[tr(lang,'policy'),rules.VERSION]]}
    tabs[tr(lang,'data_card')].append([tr(lang,'reference_end'),rules.RESPONSIBILITY_POLICY['version']])
    coverage = [[tr(lang,'source'),tr(lang,'rows')]]+[[key,n] for key,n in json.loads(snapshot['inspected']).items()]

    def details(index, selected):
        for case in selected:
            g = case['goals'][index]
            row = [case['home'] if index==2 else case['id'],case['worker'] if index!=2 else None,
                   case['entry'].year if case['entry'] and index!=2 else None,
                   g['deadline'],g['achieved'],tr(lang,g['reason']),
                   ', '.join(f'{dataset}:{line}' for dataset,line in g['evidence']),tr(lang,g['state'])]
            if index==0:
                due = {True:'due_now',False:'upcoming_due',None:'due_unknown'}[g.get('due')]
                dates = ', '.join(map(str,g.get('official_dates',())))
                row += [case['entry'],tr(lang,g['scope']),tr(lang,due) if g['scope']=='scope_in' else None,
                        dates or None,tr(lang,'undated_proof') if g.get('official_undated') else None,
                        tr(lang,'uncertain_proof') if g.get('proof_uncertain') else None]
            elif index==1:
                row += [', '.join(map(str,g.get('official_dates',()))) or None,
                        tr(lang,'undated_proof') if g.get('official_undated') else None,
                        case['reference_end'],case['transition_end'],g['earliest']]
            else:
                row[6] = ', '.join(f'{dataset}:{line}' for dataset,line in g['evidence'] if dataset!='official')
                row += [g.get('period_start'),g['earliest']]
            yield row
    for i,key in enumerate(keys):
        selected = {c['home']:c for c in cases if c['goals'][i]['state']!='na'}.values() if i==2 else cases
        summary = rules.counts(cases,i)
        tabs[tr(lang,key)] = [[tr(lang,key),tr(lang,'rows')]] + [
            [tr(lang,state),number] for state,number in sorted(summary.items())
            if role!='manager' or (snapshot['source']=='synthetic' and number>=rules.MIN_GROUP)]
        if role!='manager':
            headers = ['ID',*[tr(lang,k) for k in ('worker','year','deadline','attained','reason','evidence')],tr(lang,'goals')]
            if i==0:
                headers.extend(tr(lang,k) for k in ('entry_date','scope','due_status','official_dates','undated_proof','uncertain_proof'))
            elif i==1:
                headers.extend(tr(lang,k) for k in ('official_dates','undated_proof','reference_end','transition_end','scenario'))
            else:
                headers.extend(tr(lang,k) for k in ('period_start','scenario'))
            tabs[f'{i+1} · {tr(lang,"evidence")}'] = chain([headers],details(i,selected))
    if role!='manager':
        for field, label in (('worker','worker'),('entry','year')):
            groups = {}
            for case in cases:
                v = case[field]
                key = v.year if field=='entry' and v else v
                groups.setdefault(str(key or '—'),[]).append(case)
            tabs[tr(lang,label)] = [[tr(lang,label),*(tr(lang,k) for k in rules.A1_TOTALS)]] + [
                [key,*rules.a1_totals(items)] for key,items in sorted(groups.items())]
        tabs[tr(lang,'control_totals')] = [[tr(lang,k) for k in rules.A1_TOTALS],rules.a1_totals(cases)]
        tabs['ZEMIS'] = [[tr(lang,'case_identifier'),'ZEMIS',tr(lang,'result'),tr(lang,'evidence')]] + [
            [case['id'],line,tr(lang,reason),','.join(map(str,workbook_rows))]
            for case in cases for line,reason,workbook_rows in case['zemis_findings']]
    tabs[tr(lang,'coverage')] = coverage
    return tabs
