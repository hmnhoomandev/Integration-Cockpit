"""Server-rendered German, English and French interface."""
from html import escape, unescape
from urllib.parse import urlencode, quote, parse_qs, urlsplit
from itertools import chain
from datetime import date

from . import rules
from .xlsx import Cell
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
 'brand_context':('Behörden im Projektkontext','Public authorities referenced by this project','Autorités publiques citées dans le projet'),
 'brand_independence':('Eigenständiger Hackathon-Prototyp','Independent hackathon prototype','Prototype indépendant du hackathon'),
 'sem_name':('Staatssekretariat für Migration','State Secretariat for Migration','Secrétariat d’État aux migrations'),
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
 'course_early':('Sprachkurs in den ersten 6 Monaten','Language course within 6 months of entry','Cours de langue dans les 6 mois après l’arrivée'),
 'course_late':('Sprachkurs erst nach 6 Monaten','Language course after more than 6 months','Cours de langue après plus de 6 mois'),
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


COPY.update({
 # Worker queue and next steps. Placeholders are filled with escaped values by say().
 'queue_lead':('Wen rufe ich diese Woche an, und warum?','Who do I call this week, and why?','Qui dois-je appeler cette semaine, et pourquoi ?'),
 'this_week':('Diese Woche','This week','Cette semaine'),
 'this_week_note':('{n} Kontakte, sortiert nach Wirkung: zuerst Fristen, die noch zu retten sind, dann fehlende Einträge für die Abgeltung.',
                   '{n} contacts, ordered by impact: deadlines that can still be met first, then records missing for payment.',
                   '{n} contacts, triés par impact : d’abord les délais encore tenables, puis les enregistrements manquants pour le paiement.'),
 'show_all_week':('Alle {n} anzeigen','Show all {n}','Afficher les {n}'),
 'all_cases':('Alle Fälle','All cases','Tous les dossiers'),
 'next_step':('Nächster Schritt','Next step','Prochaine étape'),
 'when':('Termin','Date','Échéance'),
 'lights_header':('Ampel: A1 · Arbeit · Haushalt','Lights: A1 · Work · Household','Feux : A1 · Travail · Ménage'),
 'ampel_legend':('Ampel: grün erreicht · gelb auf Kurs · rot gefährdet oder Frist verpasst · grau nicht relevant · violett ? Daten prüfen',
                 'Traffic light: green reached · yellow on track · red at risk or deadline missed · grey not applicable · purple ? check data',
                 'Feu : vert atteint · jaune en bonne voie · rouge à risque ou délai dépassé · gris non concerné · violet ? données à vérifier'),
 'in_days':('in {n} Tagen','in {n} days','dans {n} jours'),
 'days_ago':('vor {n} Tagen','{n} days ago','il y a {n} jours'),
 'today':('heute','today','aujourd’hui'),
 'week':('Diese Woche','This week','Cette semaine'),
 'act_g1_risk':('A1-Frist am {date} (in {days} Tagen): telc- oder fide-Prüfung anmelden',
                'A1 deadline {date} (in {days} days): book a telc or fide exam',
                'Délai A1 le {date} (dans {days} jours) : inscrire à un examen telc ou fide'),
 'act_g1_record':('A1-Nachweis vom {date} liegt vor, fehlt aber in der Integrationszielerreichung: nachtragen, damit abgegolten wird',
                  'A1 proof dated {date} is on file but missing from Integrationszielerreichung: record it so it can be paid',
                  'Justificatif A1 du {date} présent mais absent d’Integrationszielerreichung : l’enregistrer pour le paiement'),
 'act_g1_verify':('Zertifikat ohne telc/fide-Vermerk oder ohne Datum: Original prüfen',
                  'Certificate without a telc/fide note or date: check the original',
                  'Certificat sans mention telc/fide ou sans date : vérifier l’original'),
 'act_goal_record':('{goal} rechnerisch erreicht am {date}, kein offizieller Eintrag: Nachweis erfassen',
                    '{goal} reached on {date} by the rules, but not officially recorded: record the evidence',
                    '{goal} atteint le {date} selon les règles, sans enregistrement officiel : saisir le justificatif'),
 'act_zemis':('ZEMIS meldet eine Stelle, die in Erwerb fehlt: Arbeitsvertrag einholen',
              'ZEMIS reports a job that is missing from Erwerb: ask for the employment contract',
              'ZEMIS signale un emploi absent d’Erwerb : demander le contrat de travail'),
 'act_g2_verify':('Pensum oder Erwerbsstatus fehlt: Arbeitsvertrag prüfen','Workload or employment status missing: check the contract',
                  'Taux ou statut d’emploi manquant : vérifier le contrat'),
 'act_g2_soon':('Stelle läuft: Ziel 2 am {date} erreicht, wenn sie ohne Unterbruch weiterläuft',
                'Job ongoing: goal 2 is reached on {date} if it continues without a break',
                'Emploi en cours : objectif 2 atteint le {date} s’il continue sans interruption'),
 'act_scope':('Status, Geburts- oder Einreisedatum unklar: Daten im Fallführungssystem korrigieren',
              'Status, birth or entry date unclear: correct the record in the case system',
              'Statut, date de naissance ou d’arrivée incertains : corriger le dossier'),
 'act_g3_review':('Haushalt: Unterstützungsverlauf oder Zuständigkeitsende unklar, prüfen',
                  'Household: assistance history or end of responsibility unclear, review',
                  'Ménage : historique d’aide ou fin de prise en charge incertains, à vérifier'),
 'act_g1_plan':('A1-Frist am {date} (in {days} Tagen): Kurs und Prüfung planen','A1 deadline {date} (in {days} days): plan course and exam',
                'Délai A1 le {date} (dans {days} jours) : planifier cours et examen'),
 'act_g1_missed':('A1-Frist am {date} verpasst: Sprachförderung weiterführen, keine Abgeltung mehr',
                  'A1 deadline {date} missed: continue language support, no longer payable',
                  'Délai A1 du {date} dépassé : poursuivre le soutien linguistique, plus de paiement'),
 'act_none':('Kein Handlungsbedarf','No action needed','Aucune action requise'),
 # Case explanations
 'what_means':('Was heisst das?','What does this mean?','Qu’est-ce que cela signifie ?'),
 'exp_achieved':('Erreicht am {achieved}, vor der Frist vom {deadline}.','Reached on {achieved}, before the deadline of {deadline}.',
                 'Atteint le {achieved}, avant le délai du {deadline}.'),
 'exp_late':('Erreicht am {achieved}, aber nach der Frist vom {deadline}. Keine Abgeltung.','Reached on {achieved}, but after the deadline of {deadline}. Not payable.',
             'Atteint le {achieved}, mais après le délai du {deadline}. Pas de paiement.'),
 'exp_ontrack':('Noch nicht erreicht. Frist am {deadline}, noch {days} Tage.','Not reached yet. Deadline {deadline}, {days} days left.',
                'Pas encore atteint. Délai le {deadline}, encore {days} jours.'),
 'exp_risk':('Noch nicht erreicht, und die Frist am {deadline} ist in {days} Tagen.','Not reached, and the deadline {deadline} is in {days} days.',
             'Pas atteint, et le délai du {deadline} est dans {days} jours.'),
 'exp_overdue':('Die Frist am {deadline} ist seit {days} Tagen abgelaufen, ohne gültigen Nachweis.','The deadline {deadline} passed {days} days ago without valid evidence.',
                'Le délai du {deadline} est dépassé depuis {days} jours, sans justificatif valable.'),
 'exp_review':('Das Tool kann dieses Ziel nicht sicher beurteilen: {reason}.','The tool cannot assess this goal reliably: {reason}.',
               'L’outil ne peut pas évaluer cet objectif de façon fiable : {reason}.'),
 'exp_na':('Nicht relevant: {reason}.','Not applicable: {reason}.','Non concerné : {reason}.'),
 'exp_official_yes':('Offiziell erfasst in Integrationszielerreichung am {dates}.','Officially recorded in Integrationszielerreichung on {dates}.',
                     'Enregistré officiellement dans Integrationszielerreichung le {dates}.'),
 'exp_official_no':('Kein offizieller Eintrag in Integrationszielerreichung.','No official record in Integrationszielerreichung.',
                    'Aucun enregistrement officiel dans Integrationszielerreichung.'),
 'evidence_rows':('Nachweise aus den Exporten','Evidence from the exports','Justificatifs des exports'),
 'no_evidence':('Keine passenden Zeilen in den Exporten.','No matching rows in the exports.','Aucune ligne correspondante dans les exports.'),
 'row':('Zeile','row','ligne'),
 'open':('offen','open','en cours'),
 'household_id':('Haushalt (Dossier-Nr.)','Household (Dossier-Nr.)','Ménage (Dossier-Nr.)'),
 'status_label':('Verfahrensstand','Residence status','Statut de séjour'),
 'age_label':('Alter','Age','Âge'),
 'zemis_job':('ZEMIS: {company} ab {date}','ZEMIS: {company} from {date}','ZEMIS : {company} dès le {date}'),
 # Help for every control ("!" buttons)
 'help_label':('Hilfe','Help','Aide'),
 'help_overview':('Öffnet die Übersicht: Kennzahlen, Ampel der drei Ziele und Gruppenanalyse zum gewählten Stichtag.',
                  'Opens the overview: key figures, traffic lights for the three goals and the group analysis for the chosen report date.',
                  'Ouvre la vue d’ensemble : chiffres clés, feux des trois objectifs et analyse de groupes à la date choisie.'),
 'help_queue':('Öffnet die Fallliste: wen Sie diese Woche kontaktieren sollten und warum, mit Ampel pro Ziel.',
               'Opens the case list: who to contact this week and why, with a traffic light per goal.',
               'Ouvre la liste des dossiers : qui contacter cette semaine et pourquoi, avec un feu par objectif.'),
 'help_reports':('Monatsexporte (11 Excel-Dateien) einlesen, Stichtag wählen und Ergebnisse als Excel herunterladen.',
                 'Import the monthly exports (11 Excel files), choose the report date and download the results as Excel.',
                 'Importer les exports mensuels (11 fichiers Excel), choisir la date et télécharger les résultats en Excel.'),
 'help_ai':('Erklärt die Regeln mit Quelle und beantwortet feste Fragen zu Gruppen. Läuft lokal, ohne Sprachmodell.',
            'Explains the rules with their source and answers fixed questions about groups. Runs locally, without a language model.',
            'Explique les règles avec leur source et répond à des questions fixes sur les groupes. Fonctionne localement, sans modèle de langage.'),
 'help_forecast':('Prognose der Fallzahlen, Szenario 2027 und geschätzte Abgeltung.','Workload forecast, the 2027 scenario and an estimate of payments.',
                  'Prévision de la charge, scénario 2027 et estimation des paiements.'),
 'help_intake':('Situationsanalyse als PDF lokal auslesen. Ein Vorschlag wird erst nach Ihrer Bestätigung gespeichert.',
                'Read a Situationsanalyse PDF locally. A suggestion is saved only after you confirm it.',
                'Lire une Situationsanalyse PDF localement. Une proposition n’est enregistrée qu’après votre confirmation.'),
 'help_language':('Wechselt die Sprache der Oberfläche. Die Daten und die Originalbegriffe aus den Exporten bleiben gleich.',
                  'Switches the interface language. The data and the original terms from the exports stay the same.',
                  'Change la langue de l’interface. Les données et les termes originaux des exports restent identiques.'),
 'help_logout':('Meldet Sie ab und beendet die Sitzung.','Signs you out and ends the session.','Vous déconnecte et termine la session.'),
 'help_snapshot':('Der Stichtag ist das Datum des Monatsexports. Alle Fristen und Ampeln werden auf dieses Datum berechnet.',
                  'The report date is the date of the monthly export. All deadlines and lights are calculated for this date.',
                  'La date de référence est celle de l’export mensuel. Tous les délais et feux sont calculés à cette date.'),
 'help_factor':('Wählt Ziel und Merkmal für die Gruppenanalyse. Gruppen unter 8 Personen werden zum Schutz ausgeblendet.',
                'Chooses the goal and the characteristic for the group analysis. Groups under 8 people are hidden for privacy.',
                'Choisit l’objectif et la caractéristique de l’analyse. Les groupes de moins de 8 personnes sont masqués.'),
 'help_aggregates':('Lädt die angezeigte Gruppenanalyse als Excel herunter: nur Summen, keine Personen.',
                    'Downloads the group analysis shown as Excel: totals only, no individuals.',
                    'Télécharge l’analyse affichée en Excel : uniquement des totaux, aucune personne.'),
 'help_search':('Sucht nach Fallkennung. Der Filter zeigt nur Fälle mit dieser A1-Ampel oder nur die Liste «Diese Woche».',
                'Searches by case ID. The filter shows only cases with that A1 light, or only the “This week” list.',
                'Recherche par identifiant. Le filtre n’affiche que les dossiers avec ce feu A1, ou la liste « Cette semaine ».'),
 'help_reset':('Entfernt Suche und Filter.','Clears search and filter.','Efface la recherche et le filtre.'),
 'help_case_link':('Ein Klick auf eine Fallkennung öffnet die Details: Erklärung pro Ziel und die Exportzeilen, auf denen das Ergebnis beruht.',
                   'Clicking a case ID opens its details: an explanation per goal and the export rows behind each result.',
                   'Un clic sur un identifiant ouvre le détail : explication par objectif et lignes d’export à l’origine du résultat.'),
 'help_week':('Berechnet aus Fristen und fehlenden Nachweisen, nie aus persönlichen Merkmalen wie Herkunft oder Alter.',
              'Calculated from deadlines and missing evidence, never from personal traits such as origin or age.',
              'Calculé à partir des délais et des justificatifs manquants, jamais de traits personnels comme l’origine ou l’âge.'),
 'help_back':('Zurück zur Fallliste.','Back to the case list.','Retour à la liste des dossiers.'),
 'help_choose_snapshot':('Zeigt einen früher importierten Monat an. Die Daten werden dabei nicht verändert.',
                         'Shows a month imported earlier. The data is not changed.',
                         'Affiche un mois importé auparavant. Les données ne sont pas modifiées.'),
 'help_seed':('Lädt einen erfundenen Demo-Monat neu. So sehen Sie, was sich von September zu Oktober ändert.',
              'Reloads an invented demo month, so you can see what changes from September to October.',
              'Recharge un mois de démonstration fictif pour voir ce qui change de septembre à octobre.'),
 'help_invalid':('Testet einen absichtlich unvollständigen Import. Er wird abgelehnt und der bisherige Stand bleibt erhalten.',
                 'Tests a deliberately incomplete import. It is rejected and the previous results stay in place.',
                 'Teste une importation volontairement incomplète. Elle est refusée et les résultats précédents restent en place.'),
 'help_upload':('Wählen Sie die 11 Excel-Exporte des Monats und den Stichtag. Das Tool prüft Spalten, Daten und Verknüpfungen und übernimmt nur einen fehlerfreien Import.',
                'Choose the 11 Excel exports of the month and the report date. The tool checks columns, dates and links and only accepts an import without errors.',
                'Choisissez les 11 exports Excel du mois et la date. L’outil vérifie colonnes, dates et liens et n’accepte qu’une importation sans erreur.'),
 'help_export':('Excel mit Ergebnis pro Person und Ziel, Summen pro Sozialarbeiter:in und Einreisejahr sowie Kontrollsummen.',
                'Excel with the result per person and goal, totals per social worker and entry year, and control totals.',
                'Excel avec le résultat par personne et objectif, totaux par assistant·e social·e et année d’arrivée, et totaux de contrôle.'),
 'help_quality':('Excel mit Importprotokoll: erkannte Dateien, Zeilenzahl, Prüfsumme und Fehler pro Zeile.',
                 'Excel with the import log: files recognised, row counts, checksums and errors per row.',
                 'Excel avec le journal d’importation : fichiers reconnus, nombre de lignes, sommes de contrôle et erreurs par ligne.'),
 'help_fingerprint':('Zeigt die Prüfsumme jeder Datei. Dieselbe Datei ergibt dieselbe Prüfsumme, so wird ein doppelter Import erkannt.',
                     'Shows each file’s checksum. The same file gives the same checksum, so a repeated import is detected.',
                     'Affiche la somme de contrôle de chaque fichier. Un même fichier donne la même somme, ce qui détecte les doublons.'),
 'help_topics':('Wählt die Regel, die erklärt werden soll. Die Antwort zitiert die Quelle mit Seite.',
                'Chooses the rule to explain. The answer cites the source with its page.',
                'Choisit la règle à expliquer. La réponse cite la source avec sa page.'),
 'help_rule_date':('Zeigt die Regel, wie sie an diesem Datum gilt, zum Beispiel vor und nach der Änderung 2027.',
                   'Shows the rule as it applies on that date, for example before and after the 2027 change.',
                   'Affiche la règle applicable à cette date, par exemple avant et après le changement de 2027.'),
 'help_intents':('Feste Fragen zu Gruppen. Die Antworten kommen aus geschützten Summen, nie aus Einzelfällen.',
                 'Fixed questions about groups. Answers come from protected totals, never from individual cases.',
                 'Questions fixes sur les groupes. Les réponses proviennent de totaux protégés, jamais de cas individuels.'),
 'help_data_card':('Zeigt die Monatsreihe und ihre Herkunft, auf der die Prognose beruht.','Shows the monthly series behind the forecast and where it comes from.',
                   'Affiche la série mensuelle de la prévision et son origine.'),
 'help_pricing':('Tragen Sie einen angenommenen Betrag pro Ziel ein, um die Abgeltung zu schätzen. Nur zur Illustration, keine offiziellen Tarife.',
                 'Enter an assumed amount per goal to estimate payments. Illustration only, not official rates.',
                 'Saisissez un montant supposé par objectif pour estimer les paiements. Illustration seulement, pas de tarifs officiels.'),
 'help_csv':('Ersetzt die erfundene Prognosereihe durch eigene Monatszahlen (CSV mit month,count). Nur Summen, keine Personen.',
             'Replaces the invented forecast series with your own monthly counts (CSV with month,count). Totals only, no individuals.',
             'Remplace la série fictive par vos propres chiffres mensuels (CSV month,count). Uniquement des totaux.'),
 'help_csv_reset':('Stellt die erfundene Prognosereihe wieder her.','Restores the invented forecast series.','Rétablit la série de prévision fictive.'),
 'help_pdf':('Liest eine ausgefüllte Situationsanalyse lokal aus und schlägt eine Kategorie vor. Nichts verlässt diesen Computer.',
             'Reads a completed Situationsanalyse locally and suggests a category. Nothing leaves this computer.',
             'Lit une Situationsanalyse remplie localement et propose une catégorie. Rien ne quitte cet ordinateur.'),
 'help_pdf_sample':('Testet das Auslesen mit einem erfundenen Beispiel-PDF.','Tests the extraction with an invented sample PDF.',
                    'Teste la lecture avec un PDF d’exemple fictif.'),
 'help_manual':('Für gescannte oder unlesbare PDFs: ZEMIS-Nummer und Kategorie von Hand erfassen.',
                'For scanned or unreadable PDFs: enter the ZEMIS number and category by hand.',
                'Pour les PDF scannés ou illisibles : saisir manuellement le numéro ZEMIS et la catégorie.'),
 'help_review_save':('Speichert die von Ihnen bestätigte Kategorie für diese Person.','Saves the category you confirmed for this person.',
                     'Enregistre la catégorie que vous avez confirmée pour cette personne.'),
 'help_persona':('Wechselt die Demo-Rolle: Sozialarbeiter:in sieht nur eigene Fälle, Leitung nur Summen, Import nur Daten.',
                 'Switches the demo role: a social worker sees only their own cases, management only totals, import only data.',
                 'Change le rôle de démo : assistant·e social·e voit ses dossiers, la direction les totaux, l’import les données.'),
 'help_login':('Melden Sie sich mit dem erhaltenen Konto an. Ohne Anmeldung sind keine Daten sichtbar.',
               'Sign in with the account you were given. No data is visible without signing in.',
               'Connectez-vous avec le compte reçu. Aucune donnée n’est visible sans connexion.'),
})

COPY.update({
 'targets_title':('Stufe 1 · Ziel 1: Ist und Soll','Level 1 · Goal 1: target vs actual','Niveau 1 · Objectif 1 : prévu et réalisé'),
 'targets_lead':('Wer ist betroffen, wessen Frist ist abgelaufen, wer hat A1 rechtzeitig erreicht.',
                 'Who is in scope, whose deadline has passed, and who reached A1 in time.',
                 'Qui est concerné, quel délai est échu, et qui a atteint A1 à temps.'),
 'by_worker':('pro Sozialarbeiter:in','per social worker','par assistant·e social·e'),
 'by_year':('pro Einreisejahr','per entry year','par année d’arrivée'),
 'col_scope':('Betroffen','In scope','Concernés'),
 'col_due':('Soll: Frist abgelaufen','Should have by now','Délai échu'),
 'col_ontime':('Ist: fristgerecht','Reached in time','Atteint à temps'),
 'col_late':('Verspätet','Late','En retard'),
 'col_missed':('Frist verpasst','Missed','Manqué'),
 'col_open':('Frist noch offen','Not yet due','Pas encore échu'),
 'col_review':('Prüfen','Review','À vérifier'),
 'col_rate':('Soll erfüllt','Target met','Objectif atteint'),
 'col_mix':('Ampel','Lights','Feux'),
 'total':('Total','Total','Total'),
 'field':('Angabe','Item','Élément'),
 'value':('Wert','Value','Valeur'),
 'targets_note':('«Soll erfüllt» = fristgerecht erreicht ÷ Personen, deren Frist am Stichtag abgelaufen ist. Die Summen stimmen mit dem Excel-Export überein.',
                 '“Target met” = reached in time ÷ people whose deadline has passed on the report date. The totals match the Excel export.',
                 '« Objectif atteint » = atteint à temps ÷ personnes dont le délai est échu à la date de référence. Les totaux correspondent à l’export Excel.'),
 'help_targets':('Zeigt pro Sozialarbeiter:in und pro Einreisejahr, wie viele Personen A1 bis zur Frist erreicht haben. Gleiche Zahlen wie im Excel-Export.',
                 'Shows per social worker and per entry year how many people reached A1 by their deadline. Same figures as the Excel export.',
                 'Montre par assistant·e social·e et par année d’arrivée combien de personnes ont atteint A1 à temps. Mêmes chiffres que l’export Excel.'),
 'level2_title':('Stufe 2 · Was haben Personen gemeinsam, die das Ziel erreichen?','Level 2 · What do people who reach the goal have in common?',
                 'Niveau 2 · Qu’ont en commun les personnes qui atteignent l’objectif ?'),
 'insight':('Höchste Quote: {high} mit {high_rate} (n = {high_n}). Tiefste: {low} mit {low_rate} (n = {low_n}). Unterschied {diff} Prozentpunkte.',
            'Highest rate: {high} at {high_rate} (n = {high_n}). Lowest: {low} at {low_rate} (n = {low_n}). Difference {diff} percentage points.',
            'Taux le plus élevé : {high} avec {high_rate} (n = {high_n}). Le plus bas : {low} avec {low_rate} (n = {low_n}). Écart {diff} points.'),
 'insight_clear':('Die Unsicherheitsbereiche überschneiden sich nicht: ein deutlicher Zusammenhang, aber keine bewiesene Ursache.',
                  'The uncertainty ranges do not overlap: a clear association, but not a proven cause.',
                  'Les intervalles ne se chevauchent pas : une association nette, mais pas une cause prouvée.'),
 'insight_overlap':('Die Unsicherheitsbereiche überschneiden sich: der Unterschied kann zufällig sein.',
                    'The uncertainty ranges overlap: the difference may be due to chance.',
                    'Les intervalles se chevauchent : l’écart peut être dû au hasard.'),
 'rate_chart':('Quote fristgerecht (Balken) mit 95 %-Bereich (Rahmen)','On-time rate (bar) with 95 % range (outline)','Taux à temps (barre) avec intervalle à 95 % (contour)'),
 'synthetic_patterns':('Demo-Daten: Die Zusammenhänge wurden absichtlich erzeugt, damit die Analyse etwas zeigt. Liste in docs/SOURCES.md.',
                       'Demo data: the associations were planted on purpose so the analysis has something to show. Listed in docs/SOURCES.md.',
                       'Données de démo : les associations ont été créées exprès pour que l’analyse montre quelque chose. Liste dans docs/SOURCES.md.'),
})

COPY.update({
 'forecast':('Planung','Planning','Planification'),
 'help':('Hilfe','Help','Aide'),
 'privacy':('Datenschutz','Data protection','Protection des données'),
 'help_help':('Rundgang Schritt für Schritt und Begriffe wie A1, Ampel oder Soll/Ist einfach erklärt.',
              'A step-by-step tour and plain explanations of terms such as A1, lights or target vs actual.',
              'Visite pas à pas et explication simple des termes comme A1, feux ou objectif/réalisé.'),
 'help_privacy':('Wo die Daten liegen, wer was sieht und was das Netz verlässt.','Where the data stays, who sees what and what leaves the network.',
                 'Où restent les données, qui voit quoi et ce qui quitte le réseau.'),
 'help_forecast':('Abgeltung, Szenario 2027, ZEMIS-Abgleich und Prognose der Neuzugänge auf einer Seite.',
                  'Payments, the 2027 scenario, the ZEMIS check and the arrivals forecast on one page.',
                  'Paiements, scénario 2027, contrôle ZEMIS et prévision des arrivées sur une page.'),
 'plan_lead':('Was bringt das Erreichte ein, was ändert 2027, wo fehlen Meldungen und wie viele Personen kommen neu?',
              'What do achieved goals earn, what changes in 2027, where are reports missing and how many people will arrive?',
              'Que rapportent les objectifs atteints, que change 2027, où manquent des annonces et combien de personnes arrivent ?'),
 'help_jump':('Springt direkt zum Abschnitt auf dieser Seite.','Jumps straight to that section of this page.','Va directement à cette section de la page.'),
 'pay_title':('Abgeltung','Payments','Paiements'),
 'pay_lead':('Gezählt wird nur, was fristgerecht erreicht und mit gleichem Datum in Integrationszielerreichung erfasst ist. Ziel 3 zählt einmal pro Haushalt.',
             'Only goals reached on time and recorded with the same date in Integrationszielerreichung count. Goal 3 counts once per household.',
             'Seuls les objectifs atteints à temps et saisis à la même date dans Integrationszielerreichung comptent. L’objectif 3 compte une fois par ménage.'),
 'pay_total':('Total abrechenbar','Total payable','Total facturable'),
 'pay_open':('{n} erreichte Ziele sind noch nicht abrechenbar, weil der offizielle Eintrag fehlt oder abweicht. Nachgetragen wären das bis zu {amount}.',
             '{n} reached goals cannot be claimed yet because the official record is missing or differs. Recorded, that is up to {amount}.',
             '{n} objectifs atteints ne sont pas encore facturables, car la saisie officielle manque ou diffère. Une fois saisis : jusqu’à {amount}.'),
 'pay_open_link':('Fälle mit fehlendem Eintrag öffnen','Open cases with a missing record','Ouvrir les dossiers sans saisie'),
 'scen_lead':('Ab 1. Januar 2027 endet die Zuständigkeit für VA und F-FL fünf statt sieben Jahre nach der Einreise. Annahme der Demo: gilt für alle laufenden Fälle.',
              'From 1 January 2027, responsibility for VA and F-FL ends five instead of seven years after entry. Demo assumption: it applies to all open cases.',
              'Dès le 1er janvier 2027, la prise en charge des AP et réfugiés AP prend fin cinq ans au lieu de sept après l’arrivée. Hypothèse de la démo : tous les dossiers en cours.'),
 'scen_changed':('Personen mit früherem Zuständigkeitsende','People whose responsibility ends earlier','Personnes dont la prise en charge finit plus tôt'),
 'scen_overdue':('Ziele sofort überfällig','Goals overdue at once','Objectifs aussitôt en retard'),
 'scen_risk':('Ziele neu gefährdet','Goals newly at risk','Objectifs nouvellement en danger'),
 'scen_household':('{n} Personen ohne Einreisedatum übernehmen die neue Frist ihres Haushalts, weil alle Mitglieder dasselbe exportierte Ende haben.',
                   '{n} people without an entry date take their household’s new cutoff, because all members share the same exported end.',
                   '{n} personnes sans date d’arrivée reprennent la nouvelle échéance de leur ménage, car tous les membres ont la même fin exportée.'),
 'scen_confirm':('Welche Kohorten betroffen sind, muss das ASD bestätigen. Die Regel steht in cockpit/responsibility-policy.json und lässt sich ohne Programmänderung anpassen.',
                 'ASD must confirm which cohorts are affected. The rule lives in cockpit/responsibility-policy.json and can be changed without touching the code.',
                 'L’ASD doit confirmer les cohortes concernées. La règle se trouve dans cockpit/responsibility-policy.json et se modifie sans toucher au code.'),
 'help_scenario':('Vergleicht jedes Ziel mit heutiger Frist (Basis) und mit der Frist ab 2027 (Szenario). Die importierten Daten bleiben unverändert.',
                  'Compares each goal under today’s cutoff (baseline) and the 2027 cutoff (scenario). The imported data stay unchanged.',
                  'Compare chaque objectif avec l’échéance actuelle (référence) et celle de 2027 (scénario). Les données importées ne changent pas.'),
 'zemis_title':('ZEMIS-Abgleich','ZEMIS check','Contrôle ZEMIS'),
 'zemis_lead':('Stellen, die in ZEMIS gemeldet sind, werden mit den Einträgen in Erwerb verglichen. Abweichungen können Ziel 2 und die Abgeltung verfälschen.',
               'Jobs reported in ZEMIS are compared with the entries in Erwerb. Mismatches can distort goal 2 and payments.',
               'Les emplois annoncés dans ZEMIS sont comparés aux saisies d’Erwerb. Les écarts peuvent fausser l’objectif 2 et les paiements.'),
 'zemis_people':('Personen mit Abweichung','People with a mismatch','Personnes avec un écart'),
 'zemis_none':('Keine Abweichungen zum Stichtag.','No mismatches on the report date.','Aucun écart à la date de référence.'),
 'zemis_link':('Diese Fälle in der Fallführung öffnen','Open these cases in casework','Ouvrir ces dossiers dans le suivi'),
 'record':('Eintrag für Abgeltung fehlt','Payment record missing','Saisie pour paiement manquante'),
 'zemis':('ZEMIS-Abweichung','ZEMIS mismatch','Écart ZEMIS'),
 'forecast_model':('Prognosemodell','Forecast model','Modèle de prévision'),
 'calculate':('Neu berechnen','Recalculate','Recalculer'),
 'scenario_details':('Alle Ziele im Vergleich','All goals compared','Tous les objectifs comparés'),
 'pay_open_count':('{n} erreichte Ziele sind noch nicht abrechenbar, weil der offizielle Eintrag fehlt oder abweicht. Tragen Sie Ansätze ein, um den Betrag zu sehen.',
                   '{n} reached goals cannot be claimed yet because the official record is missing or differs. Enter rates to see the amount.',
                   '{n} objectifs atteints ne sont pas encore facturables, car la saisie officielle manque ou diffère. Saisissez des tarifs pour voir le montant.'),
 'help_zemis':('Zählt nur Meldungen bis zum Stichtag. Gleicher Arbeitgeber und überlappende Daten gelten als bestätigt.',
               'Counts reports up to the report date. Same employer and overlapping dates count as confirmed.',
               'Ne compte que les annonces jusqu’à la date de référence. Même employeur et dates qui se chevauchent valent confirmation.'),
 'arrivals_title':('Neuzugänge','New arrivals','Nouvelles arrivées'),
 'arrivals_lead':('Wie viele Personen kommen voraussichtlich im nächsten Monat neu dazu? Geschätzt aus der Monatsreihe, geprüft an zurückgehaltenen Monaten.',
                  'How many people are likely to arrive next month? Estimated from the monthly series and checked on held-back months.',
                  'Combien de personnes arriveront probablement le mois prochain ? Estimation tirée de la série mensuelle, vérifiée sur des mois mis de côté.'),
 'guide_lead':('So arbeiten Sie mit dem Cockpit. Die Schritte zeigen nur Bereiche, die Ihre Rolle öffnen darf.',
               'How to work with the cockpit. The steps only show areas your role may open.',
               'Comment utiliser le cockpit. Les étapes ne montrent que les espaces ouverts à votre rôle.'),
 'guide_steps':('Rundgang','Tour','Visite'),
 'guide_open':('Öffnen','Open','Ouvrir'),
 'step_reports':('Stichtag laden: die elf Excel-Exporte hochladen oder einen Demo-Monat wählen. Fehlerhafte Dateien werden abgelehnt, die letzte gültige Version bleibt.',
                 'Load a report date: upload the eleven Excel exports or pick a demo month. Faulty files are rejected and the last valid version stays.',
                 'Charger une date de référence : déposer les onze exports Excel ou choisir un mois de démo. Les fichiers erronés sont refusés, la dernière version valable reste.'),
 'step_overview':('Übersicht lesen: drei Ziele mit Ampel, Ist und Soll pro Fallführung und Einreisejahr, dann die Gruppenanalyse (Stufe 2).',
                  'Read the overview: three goals with lights, target vs actual per caseworker and entry year, then the group analysis (level 2).',
                  'Lire la vue d’ensemble : trois objectifs avec feux, objectif et réalisé par gestionnaire et année d’arrivée, puis l’analyse de groupes (niveau 2).'),
 'step_queue':('«Diese Woche» abarbeiten: oben stehen Fristen, die noch zu retten sind, dann fehlende Einträge für die Abgeltung.',
               'Work through “This week”: deadlines that can still be saved come first, then missing records for payments.',
               'Traiter « Cette semaine » : d’abord les délais encore rattrapables, puis les saisies manquantes pour les paiements.'),
 'step_case':('Fall öffnen: der nächste Schritt steht oben, darunter jede Regel mit den Quellzeilen, aus denen sie berechnet wurde.',
              'Open a case: the next step is at the top, below it each rule with the source rows it was calculated from.',
              'Ouvrir un dossier : l’étape suivante est en haut, puis chaque règle avec les lignes sources utilisées.'),
 'step_forecast':('Planung prüfen: Abgeltung, Wirkung der Regel 2027, ZEMIS-Abweichungen und erwartete Neuzugänge.',
                  'Check planning: payments, the effect of the 2027 rule, ZEMIS mismatches and expected arrivals.',
                  'Vérifier la planification : paiements, effet de la règle 2027, écarts ZEMIS et arrivées attendues.'),
 'step_intake':('Situationsanalyse auswerten: PDF lokal lesen, Kategorie bestätigen. Erst dann fliesst sie in die Analyse ein.',
                'Review an intake form: read the PDF locally and confirm the category. Only then does it enter the analysis.',
                'Analyser une situation : lire le PDF localement, confirmer la catégorie. Elle n’entre dans l’analyse qu’ensuite.'),
 'step_ai':('Regeln nachschlagen: Quelle und gültige Fassung jeder Regel, ohne Personendaten.',
            'Look up rules: the source and valid version of each rule, without personal data.',
            'Consulter les règles : source et version valable de chaque règle, sans données personnelles.'),
 'glossary':('Begriffe','Terms','Termes'),
 'g_a1':('Ziel 1 · Sprache A1','Goal 1 · Language A1','Objectif 1 · Langue A1'),
 'g_a1_text':('Personen ab 16 mit VA oder F-FL brauchen innert drei Jahren nach Einreise einen A1-Nachweis (z. B. fide, telc).',
              'People aged 16+ with VA or F-FL need A1 proof (e.g. fide, telc) within three years of entry.',
              'Les personnes de 16 ans et plus avec AP ou réfugié AP doivent prouver le niveau A1 (p. ex. fide, telc) dans les trois ans après l’arrivée.'),
 'g_work':('Ziel 2 · Arbeit oder Ausbildung','Goal 2 · Work or education','Objectif 2 · Travail ou formation'),
 'g_work_text':('Sechs Monate ohne Unterbruch mindestens 60 % im ersten Arbeitsmarkt oder eine Ausbildung Sek II / Tertiär vor Zuständigkeitsende.',
                'Six uninterrupted months at 60 %+ in the primary labour market, or upper-secondary/tertiary education before responsibility ends.',
                'Six mois sans interruption à 60 % ou plus sur le premier marché du travail, ou une formation secondaire II / tertiaire avant la fin de la prise en charge.'),
 'g_household':('Ziel 3 · Finanzielle Selbstständigkeit','Goal 3 · Financial independence','Objectif 3 · Autonomie financière'),
 'g_household_text':('Der ganze Haushalt (Dossier-Nr.) lebt zwölf Monate am Stück ohne Sozialhilfe vor Zuständigkeitsende.',
                     'The whole household (Dossier-Nr.) lives twelve months in a row without social assistance before responsibility ends.',
                     'Tout le ménage (Dossier-Nr.) vit douze mois d’affilée sans aide sociale avant la fin de la prise en charge.'),
 'g_lights':('Ampel','Lights','Feux'),
 'g_lights_text':('Grün erreicht · Gelb auf Kurs · Orange gefährdet · Rot überfällig oder verspätet · Violett prüfen · Grau nicht betroffen.',
                  'Green reached · yellow on track · orange at risk · red overdue or late · purple check · grey not in scope.',
                  'Vert atteint · jaune en bonne voie · orange en danger · rouge en retard · violet à vérifier · gris non concerné.'),
 'g_target':('Soll und Ist','Target and actual','Objectif et réalisé'),
 'g_target_text':('Soll: Personen, deren Frist abgelaufen ist. Ist: davon fristgerecht erreicht. Soll erfüllt ist Ist geteilt durch Soll.',
                  'Target: people whose deadline has passed. Actual: of those, reached on time. Target met is actual divided by target.',
                  'Objectif : personnes dont le délai est échu. Réalisé : parmi elles, atteint à temps. Le taux est réalisé divisé par objectif.'),
 'g_cutoff':('Stichtag und Zuständigkeitsende','Report date and end of responsibility','Date de référence et fin de prise en charge'),
 'g_cutoff_text':('Der Stichtag ist das Datum des Exports. Nach dem Zuständigkeitsende zählt ein Ziel nicht mehr für das ASD.',
                  'The report date is the export date. After responsibility ends, a goal no longer counts for ASD.',
                  'La date de référence est celle de l’export. Après la fin de prise en charge, un objectif ne compte plus pour l’ASD.'),
 'g_small':('Kleine Gruppen','Small groups','Petits groupes'),
 'g_small_text':('Gruppen mit weniger als 8 Personen werden ausgeblendet, damit niemand erkennbar wird.',
                 'Groups with fewer than 8 people are hidden so nobody can be recognised.',
                 'Les groupes de moins de 8 personnes sont masqués pour que personne ne soit reconnaissable.'),
 'g_zemis':('ZEMIS','ZEMIS','ZEMIS'),
 'g_zemis_text':('Bundesregister, in dem Arbeitgeber Stellen von Geflüchteten melden. Dient hier zur Kontrolle der Erwerbseinträge.',
                 'Federal register where employers report jobs held by refugees. Used here to check the employment entries.',
                 'Registre fédéral où les employeurs annoncent les emplois des personnes réfugiées. Sert ici à contrôler les saisies d’emploi.'),
 'pv_lead':('Das Cockpit ist so gebaut, dass Personendaten auf dem Rechner des ASD bleiben. Vor dem Echtbetrieb prüft die Datenschutzstelle der Stadt Bern.',
            'The cockpit is built so personal data stay on ASD’s own machine. Before live use, the City of Bern’s data protection office reviews it.',
            'Le cockpit est conçu pour que les données personnelles restent sur l’ordinateur de l’ASD. Avant la mise en service, le service de protection des données de la Ville de Berne l’examine.'),
 'pv_stay':('Daten bleiben lokal','Data stay local','Les données restent locales'),
 'pv_stay_text':('Eine Datei auf dem ASD-Rechner. Keine Cloud, kein externer Server.','One file on the ASD machine. No cloud, no external server.',
                 'Un fichier sur l’ordinateur de l’ASD. Pas de cloud, pas de serveur externe.'),
 'pv_roles':('Nur was die Rolle braucht','Only what the role needs','Seulement ce dont le rôle a besoin'),
 'pv_roles_text':('Fallführung sieht eigene Fälle, Leitung nur Summen. Der Server prüft das bei jedem Aufruf.',
                  'Caseworkers see their own cases, management only totals. The server checks this on every request.',
                  'Les gestionnaires voient leurs dossiers, la direction seulement des totaux. Le serveur le vérifie à chaque requête.'),
 'pv_leave':('Nichts geht automatisch hinaus','Nothing leaves automatically','Rien ne sort automatiquement'),
 'pv_leave_text':('Keine KI-Dienste, keine Statistik-Tools. Der Browser darf nur Dateien des Cockpits laden.',
                  'No AI services, no tracking tools. The browser may only load the cockpit’s own files.',
                  'Aucun service d’IA, aucun outil de suivi. Le navigateur ne charge que les fichiers du cockpit.'),
 'pv_flow':('Weg der Daten','How data flow','Parcours des données'),
 'pv_flow_1':('Excel-Exporte aus dem Fallsystem','Excel exports from the case system','Exports Excel du système de dossiers'),
 'pv_flow_2':('Prüfung beim Import: unvollständige Lieferungen werden abgelehnt','Checked on import: incomplete deliveries are rejected','Contrôle à l’import : les livraisons incomplètes sont refusées'),
 'pv_flow_3':('Speicherung in einer Datei auf dem ASD-Rechner','Stored in one file on the ASD machine','Stockage dans un fichier sur l’ordinateur de l’ASD'),
 'pv_flow_4':('Anzeige im Browser, gefiltert nach Rolle','Shown in the browser, filtered by role','Affichage dans le navigateur, filtré par rôle'),
 'pv_flow_5':('Excel-Download nur auf Klick, im gleichen Rollenumfang','Excel download only on click, within the same role scope','Téléchargement Excel seulement sur clic, dans le même périmètre'),
 'pv_who':('Wer sieht was','Who sees what','Qui voit quoi'),
 'pv_area':('Bereich','Area','Espace'),
 'pv_cases':('Fallliste und Falldetails','Case list and case details','Liste et détail des dossiers'),
 'pv_overview':('Übersicht und Analyse','Overview and analysis','Vue d’ensemble et analyse'),
 'pv_export':('Excel-Export','Excel export','Export Excel'),
 'pv_import':('Import und Qualitätsbericht','Import and quality report','Import et rapport qualité'),
 'pv_plan':('Planung','Planning','Planification'),
 'pv_intake':('Situationsanalyse','Intake review','Analyse de situation'),
 'cell_all':('Alle','All','Tous'),
 'cell_own':('Nur eigene Fälle','Own cases only','Ses dossiers seulement'),
 'cell_sums':('Nur Summen','Totals only','Totaux seulement'),
 'cell_no':('Kein Zugriff','No access','Pas d’accès'),
 'pv_stored':('Was gespeichert wird','What is stored','Ce qui est enregistré'),
 'pv_stored_1':('Die Zeilen der Exporte, pro Stichtag, damit jede Zahl auf ihre Quelle zurückführbar ist.',
                'The rows of the exports, per report date, so every number can be traced to its source.',
                'Les lignes des exports, par date de référence, pour que chaque chiffre soit traçable.'),
 'pv_stored_2':('Passwörter nur als scrypt-Hash. Sitzungen enden nach acht Stunden.','Passwords only as scrypt hashes. Sessions end after eight hours.',
                'Mots de passe uniquement sous forme de hachage scrypt. Les sessions expirent après huit heures.'),
 'pv_stored_3':('Das Protokoll hält Zeit, Aktion und Ergebnis fest, aber keine Namen oder Nummern von Klientinnen und Klienten.',
                'The log records time, action and outcome, but no client names or numbers.',
                'Le journal note l’heure, l’action et le résultat, sans noms ni numéros de clients.'),
 'pv_stored_4':('Ein Situationsanalyse-PDF wird nur im Arbeitsspeicher gelesen. Gespeichert wird allein die bestätigte Kategorie.',
                'An intake PDF is only read in memory. Only the confirmed category is stored.',
                'Un PDF d’analyse de situation n’est lu qu’en mémoire. Seule la catégorie confirmée est enregistrée.'),
 'pv_out':('Was das Netz verlässt','What leaves the network','Ce qui quitte le réseau'),
 'pv_out_1':('Automatisch nichts. Der Browser blockiert Skripte und Inhalte fremder Adressen.','Nothing automatically. The browser blocks scripts and content from other addresses.',
             'Rien automatiquement. Le navigateur bloque les scripts et contenus d’autres adresses.'),
 'pv_out_2':('Links zu BFS oder SEM öffnen sich nur auf Klick und senden keine Herkunftsadresse mit.','Links to FSO or SEM open only on click and send no referring address.',
             'Les liens vers l’OFS ou le SEM ne s’ouvrent que sur clic et n’envoient pas l’adresse d’origine.'),
 'pv_out_3':('Der Regelassistent arbeitet mit festen Quellen und lehnt Fragen mit Personendaten ab.','The rules assistant uses fixed sources and refuses questions that contain personal data.',
             'L’assistant des règles utilise des sources fixes et refuse les questions avec des données personnelles.'),
 'pv_delete':('Löschen','Deleting','Suppression'),
 'pv_delete_text':('Einen Stichtag löscht der Betrieb per Befehl. Wird die Datenbankdatei gelöscht, sind alle Daten weg.',
                   'Operations deletes a report date with one command. Deleting the database file removes all data.',
                   'L’exploitation supprime une date de référence par commande. Supprimer le fichier de base efface toutes les données.'),
 'pv_demo':('Öffentliche Demo: nur erfundene Personen. Das Hochladen echter Dateien ist dort gesperrt.',
            'Public demo: invented people only. Uploading real files is blocked there.',
            'Démo publique : personnes inventées uniquement. Le dépôt de vrais fichiers y est bloqué.'),
})

COPY.update({
 'ai_badge':('KI · lokal','AI · local','IA · locale'),
 'ai-analysis':('KI-Analyse','AI analysis','Analyse IA'),
 'help_ai-analysis':('Auswertung durch KI aus Summen, mit Schutzschild: Sie sehen genau, was gesendet wird.','AI evaluation from totals, with privacy shield: you see exactly what is sent.','Évaluation IA à partir de totaux, avec bouclier : vous voyez exactement ce qui est envoyé.'),
 'pred_title':('KI-Prognose · Sprache A1','AI forecast · Language A1','Prévision IA · Langue A1'),
 'pred_lead':('Wahrscheinlichkeit, A1 fristgerecht zu erreichen, wenn alles so weiterläuft wie bisher.',
              'Chance of reaching A1 on time if things continue as they are.',
              'Probabilité d’atteindre l’A1 dans les délais si rien ne change.'),
 'pred_base':('Durchschnitt aller abgeschlossenen Fälle: {rate}','Average of all completed cases: {rate}','Moyenne de tous les dossiers terminés : {rate}'),
 'pred_factors':('Was die Prognose am stärksten bewegt','What moves the forecast most','Ce qui influence le plus la prévision'),
 'pred_up':('erhöht','raises','augmente'),
 'pred_down':('senkt','lowers','diminue'),
 'pred_peers':('Von {n} ähnlichen Personen (gleiches Kursmuster, gleiche Altersgruppe) erreichten {k} A1 fristgerecht.',
               'Of {n} similar people (same course pattern, same age group), {k} reached A1 on time.',
               'Sur {n} personnes semblables (même parcours de cours, même tranche d’âge), {k} ont atteint l’A1 à temps.'),
 'scenario_course_now':('Wenn jetzt ein Sprachkurs startet (noch in den ersten 6 Monaten): {before} → {after}',
                        'If a language course starts now (still within the first 6 months): {before} → {after}',
                        'Si un cours de langue commence maintenant (encore dans les 6 premiers mois) : {before} → {after}'),
 'pred_model':('Logistische Regression, auf diesem Rechner trainiert mit {n} abgeschlossenen Fällen. Trefferqualität (AUC, Kreuzvalidierung) {auc}; Fehler {skill} kleiner als ein Schätzwert ohne Modell. Ohne Nationalität, Muttersprache und Geschlecht.',
               'Logistic regression trained on this machine with {n} completed cases. Discrimination (AUC, cross-validated) {auc}; error {skill} lower than a guess without the model. Nationality, mother tongue and gender are not used.',
               'Régression logistique entraînée sur cet ordinateur avec {n} dossiers terminés. Qualité (AUC, validation croisée) {auc} ; erreur inférieure de {skill} à une estimation sans modèle. Sans nationalité, langue maternelle ni sexe.'),
 'pred_caution':('Hilfe für das Gespräch, keine Entscheidung. Nie für Leistungen oder Sanktionen verwenden.',
                 'Support for the conversation, not a decision. Never use it for benefits or sanctions.',
                 'Aide pour l’entretien, pas une décision. Ne jamais l’utiliser pour des prestations ou des sanctions.'),
 'pred_none':('Die KI-Prognose erscheint nur für offene A1-Fälle (auf Kurs oder gefährdet).','The AI forecast appears only for open A1 cases (on track or at risk).',
              'La prévision IA n’apparaît que pour les dossiers A1 ouverts (en bonne voie ou en danger).'),
 'f_course_early':('Sprachkurs in den ersten 6 Monaten','Language course in the first 6 months','Cours de langue dans les 6 premiers mois'),
 'f_course_early_no':('Kein Sprachkurs in den ersten 6 Monaten','No language course in the first 6 months','Pas de cours de langue dans les 6 premiers mois'),
 'f_course_late':('Sprachkurs erst nach 6 Monaten','Language course only after 6 months','Cours de langue seulement après 6 mois'),
 'f_course_late_no':('Kein später Sprachkurs','No late language course','Pas de cours tardif'),
 'f_school_years':('Schuljahre vor Einreise: {v}','School years before entry: {v}','Années d’école avant l’arrivée : {v}'),
 'f_age_at_entry':('Alter bei Einreise: {v}','Age at entry: {v}','Âge à l’arrivée : {v}'),
 'f_latin':('Lateinisch alphabetisiert','Literate in Latin script','Alphabétisé·e en écriture latine'),
 'f_latin_no':('Nicht lateinisch alphabetisiert','Not literate in Latin script','Pas alphabétisé·e en écriture latine'),
 'f_small_children':('Kleinkind unter 8 im Haushalt','Child under 8 in the household','Enfant de moins de 8 ans dans le ménage'),
 'f_small_children_no':('Kein Kleinkind unter 8 im Haushalt','No child under 8 in the household','Pas d’enfant de moins de 8 ans dans le ménage'),
 'help_prediction':('Ein Modell lernt aus Personen, deren A1-Frist schon abgelaufen ist, und schätzt daraus die Chance für diese Person. Es läuft auf diesem Rechner; keine Daten gehen hinaus.',
                    'A model learns from people whose A1 deadline has already passed and estimates this person’s chance. It runs on this computer; no data leave it.',
                    'Un modèle apprend des personnes dont le délai A1 est déjà échu et estime la chance de cette personne. Il tourne sur cet ordinateur ; aucune donnée ne sort.'),
 'contact_title':('Kontakt','Contact','Contact'),
 'contact_demo':('Erfundene Demo-Kontaktdaten. Im Echtbetrieb kommen sie aus dem Fallsystem; die 11 Exporte enthalten keine Kontaktdaten.',
                 'Invented demo contact details. In live use they come from the case system; the 11 exports contain no contact data.',
                 'Coordonnées de démo inventées. En production, elles viennent du système de dossiers ; les 11 exports n’en contiennent pas.'),
 'call':('Anrufen','Call','Appeler'),
 'write_mail':('E-Mail schreiben','Write email','Écrire un e-mail'),
 'mail_suggested':('Empfohlene Vorlage','Suggested template','Modèle recommandé'),
 'mail_other':('Andere Vorlagen','Other templates','Autres modèles'),
 'mail_preview':('Text ansehen','Preview text','Voir le texte'),
 'mail_lang':('Sprache der Person','Person’s language','Langue de la personne'),
 'help_contact':('«Anrufen» öffnet die Telefon-App des Computers, «E-Mail» das Mailprogramm mit fertigem Text. Nichts wird automatisch gesendet: Sie prüfen und senden selbst.',
                 '“Call” opens the computer’s phone app, “Email” opens your mail program with the text filled in. Nothing is sent automatically: you check and send it yourself.',
                 '« Appeler » ouvre l’application téléphone, « E-mail » ouvre votre messagerie avec le texte prêt. Rien n’est envoyé automatiquement : vous vérifiez et envoyez vous-même.'),
 'mail_a1':('A1-Prüfung anmelden','Register for the A1 exam','Inscription à l’examen A1'),
 'mail_meeting':('Termin vereinbaren','Arrange a meeting','Fixer un rendez-vous'),
 'mail_documents':('Unterlagen nachreichen','Send documents','Envoyer des documents'),
 'shield_title':('KI-Schutzschild','AI privacy shield','Bouclier de confidentialité IA'),
 'shield_lead':('Bevor Text an eine KI geht, erkennt das Cockpit persönliche Angaben auf diesem Rechner und ersetzt sie. Findet die Endkontrolle danach noch etwas, wird nichts gesendet.',
                'Before any text goes to an AI, the cockpit detects personal details on this computer and replaces them. If the final check still finds something, nothing is sent.',
                'Avant qu’un texte parte vers une IA, le cockpit détecte les données personnelles sur cet ordinateur et les remplace. Si le contrôle final trouve encore quelque chose, rien n’est envoyé.'),
 'shield_hidden':('Verborgen','Hidden','Masqué'),
 'shield_sent':('Genau dieser Text darf die KI erreichen','Exactly this text may reach the AI','Exactement ce texte peut atteindre l’IA'),
 'shield_none':('Keine persönlichen Angaben gefunden.','No personal details found.','Aucune donnée personnelle trouvée.'),
 'ai_state_off':('Sprachmodell nicht verbunden. Das Ergebnis unten wurde lokal ohne Sprachmodell erstellt; nichts hat den Rechner verlassen.',
                 'Language model not connected. The result below was produced locally without a language model; nothing left this computer.',
                 'Modèle de langage non connecté. Le résultat ci-dessous a été produit localement sans modèle ; rien n’a quitté cet ordinateur.'),
 'ai_state_missing_sdk':('Sprachmodell eingeschaltet, aber das Paket «anthropic» fehlt. Lokales Ergebnis angezeigt.',
                         'Language model switched on, but the “anthropic” package is missing. Showing the local result.',
                         'Modèle activé, mais le paquet « anthropic » manque. Résultat local affiché.'),
 'ai_state_answered':('Antwort von Claude (Anthropic). Gesendet wurde nur der maskierte Text unten.','Answer from Claude (Anthropic). Only the masked text below was sent.',
                      'Réponse de Claude (Anthropic). Seul le texte masqué ci-dessous a été envoyé.'),
 'ai_state_blocked':('Gestoppt: Die Endkontrolle hat noch persönliche Angaben gefunden. Nichts wurde gesendet.','Stopped: the final check still found personal details. Nothing was sent.',
                     'Arrêté : le contrôle final a encore trouvé des données personnelles. Rien n’a été envoyé.'),
 'ai_state_error':('Das Sprachmodell war nicht erreichbar ({state}). Lokales Ergebnis angezeigt.','The language model could not be reached ({state}). Showing the local result.',
                   'Le modèle de langage était injoignable ({state}). Résultat local affiché.'),
 'ai_summary':('KI-Zusammenfassung','AI summary','Résumé IA'),
 'ai_local_summary':('Lokale Zusammenfassung (ohne Sprachmodell)','Local summary (no language model)','Résumé local (sans modèle de langage)'),
 'ai_analysis':('KI-Analyse','AI analysis','Analyse IA'),
 'ai_analysis_lead':('Die KI liest nur Summen und Gruppenquoten (Gruppen unter 8 Personen sind entfernt) und schreibt daraus Beobachtungen und Empfehlungen für die Leitung.',
                     'The AI reads only totals and group rates (groups under 8 people removed) and writes observations and recommendations for management.',
                     'L’IA ne lit que des totaux et des taux de groupe (groupes de moins de 8 personnes retirés) et en tire des constats et des recommandations pour la direction.'),
 'ai_analysis_open':('KI-Analyse öffnen','Open AI analysis','Ouvrir l’analyse IA'),
 'ai_refresh':('Neu erstellen','Regenerate','Régénérer'),
 'help_ai_analysis':('Erstellt eine Auswertung aus Summen, nie aus einzelnen Fällen. Sie sehen unten genau, welcher Text an die KI geht.',
                     'Writes an evaluation from totals, never from single cases. Below you see exactly which text goes to the AI.',
                     'Rédige une évaluation à partir de totaux, jamais de dossiers individuels. Vous voyez ci-dessous exactement le texte envoyé à l’IA.'),
 'local_obs_target':('Ziel 1: {met} von {due} Personen mit abgelaufener Frist haben A1 fristgerecht erreicht ({rate}).',
                     'Goal 1: {met} of {due} people whose deadline has passed reached A1 on time ({rate}).',
                     'Objectif 1 : {met} des {due} personnes au délai échu ont atteint l’A1 à temps ({rate}).'),
 'local_obs_course':('Stärkster Unterschied: {high} {high_rate} gegenüber {low} {low_rate}. Ein Zusammenhang, keine bewiesene Ursache.',
                     'Largest difference: {high} {high_rate} versus {low} {low_rate}. An association, not a proven cause.',
                     'Plus grand écart : {high} {high_rate} contre {low} {low_rate}. Une association, pas une cause prouvée.'),
 'local_obs_risk':('{n} Personen sind gefährdet: Frist in weniger als einem Jahr, noch kein Nachweis.','{n} people are at risk: deadline within a year, no proof yet.',
                   '{n} personnes sont en danger : délai dans moins d’un an, pas encore de preuve.'),
 'local_obs_record':('{n} erreichte Ziele sind noch nicht offiziell erfasst und daher nicht abrechenbar.','{n} reached goals are not yet officially recorded and so cannot be claimed.',
                     '{n} objectifs atteints ne sont pas encore saisis officiellement et ne sont donc pas facturables.'),
 'local_rec_course':('Empfehlung: Sprachkurse in den ersten sechs Monaten nach Einreise priorisieren und den Effekt mit echten Daten prüfen.',
                     'Recommendation: prioritise language courses in the first six months after entry and test the effect with real data.',
                     'Recommandation : prioriser les cours de langue dans les six premiers mois et vérifier l’effet avec des données réelles.'),
 'local_rec_record':('Empfehlung: fehlende Einträge in Integrationszielerreichung monatlich nachtragen.','Recommendation: add missing Integrationszielerreichung records every month.',
                     'Recommandation : compléter chaque mois les saisies manquantes dans Integrationszielerreichung.'),
})

COPY.update({
 'pv_leave_text':('Standardmässig geht nichts hinaus. Wird ein KI-Dienst eingeschaltet, erreicht ihn nur maskierter Text oder Summen.',
                  'By default nothing leaves. If an AI service is switched on, only masked text or totals reach it.',
                  'Par défaut, rien ne sort. Si un service d’IA est activé, il ne reçoit que du texte masqué ou des totaux.'),
 'pv_out_3':('Der Regelassistent arbeitet mit festen Quellen und lehnt Fragen mit Personendaten ab.','The rules assistant uses fixed sources and refuses questions that contain personal data.',
             'L’assistant des règles utilise des sources fixes et refuse les questions avec des données personnelles.'),
 'pv_ai':('KI und Datenschutz','AI and data protection','IA et protection des données'),
 'pv_ai_1':('Prognose pro Person: ein Modell, das auf diesem Rechner trainiert wird und läuft. Keine Daten verlassen den Rechner. Nationalität, Muttersprache und Geschlecht werden nicht verwendet.',
            'Per-person forecast: a model trained and run on this computer. No data leave it. Nationality, mother tongue and gender are not used.',
            'Prévision par personne : un modèle entraîné et exécuté sur cet ordinateur. Aucune donnée ne sort. Nationalité, langue maternelle et sexe ne sont pas utilisés.'),
 'pv_ai_2':('KI-Schutzschild: Namen, Geburtsdaten, AHV-, ZEMIS- und Klientennummern, Adressen, Telefon, E-Mail und IBAN werden lokal ersetzt, bevor Text zu einem Sprachmodell geht. Eine Endkontrolle stoppt die Anfrage, wenn noch etwas erkennbar ist.',
            'AI privacy shield: names, birth dates, AHV, ZEMIS and client numbers, addresses, phone, email and IBAN are replaced locally before text goes to a language model. A final check stops the request if anything is still recognisable.',
            'Bouclier IA : noms, dates de naissance, numéros AVS, ZEMIS et clients, adresses, téléphone, e-mail et IBAN sont remplacés localement avant tout envoi à un modèle de langage. Un contrôle final bloque la requête si quelque chose reste reconnaissable.'),
 'pv_ai_3':('Das Sprachmodell (Claude) ist ausgeschaltet, bis der Betrieb es bewusst einschaltet. Es erhält nie Fallzeilen, nur maskierte Dokumente oder Summen. Jede Anfrage steht im Protokoll, ohne Inhalt.',
            'The language model (Claude) is off until operations deliberately switch it on. It never receives case rows, only masked documents or totals. Every request is logged, without content.',
            'Le modèle de langage (Claude) est désactivé tant que l’exploitation ne l’active pas. Il ne reçoit jamais de lignes de dossier, seulement des documents masqués ou des totaux. Chaque requête est journalisée, sans contenu.'),
 'pv_ai_4':('Jede KI-Ausgabe ist ein Vorschlag. Entscheidungen trifft immer eine Fachperson.','Every AI output is a suggestion. A professional always makes the decision.',
            'Chaque résultat d’IA est une suggestion. La décision revient toujours à un·e professionnel·le.'),
})

COPY.update({
 'pred_title':('KI-Gruppenmuster · Sprache A1','AI group pattern · Language A1','Profil de groupe IA · Langue A1'),
 'pred_lead':('Wie erging es Personen in einer ähnlichen Lage? Das Cockpit zeigt Gruppen, nie eine Bewertung dieser Person.',
              'How did people in a similar situation do? The cockpit shows groups, never a score for this person.',
              'Comment s’en sont sorties les personnes dans une situation semblable ? Le cockpit montre des groupes, jamais une note pour cette personne.'),
 'pred_peers':('von {n} Personen in ähnlicher Lage (gleiches Kursmuster, gleiche Altersgruppe) erreichten A1 fristgerecht: {k}.',
               'of {n} people in a similar situation (same course pattern, same age group) reached A1 on time: {k}.',
               'des {n} personnes dans une situation semblable (même parcours de cours, même tranche d’âge) ont atteint l’A1 à temps : {k}.'),
 'pred_base':('Strich im Balken: Durchschnitt aller abgeschlossenen Fälle, {rate}.','Mark on the bar: average of all completed cases, {rate}.',
              'Repère sur la barre : moyenne de tous les dossiers terminés, {rate}.'),
 'pred_small':('Die ähnliche Gruppe ist zu klein (unter 8 Personen). Es wird kein Muster angezeigt.','The similar group is too small (under 8 people). No pattern is shown.',
               'Le groupe semblable est trop petit (moins de 8 personnes). Aucun profil n’est affiché.'),
 'scenario_course_now':('Gleiche Altersgruppe mit Sprachkurs in den ersten 6 Monaten: {rate} fristgerecht (n = {n}).',
                        'Same age group with a language course in the first 6 months: {rate} on time (n = {n}).',
                        'Même tranche d’âge avec cours de langue dans les 6 premiers mois : {rate} à temps (n = {n}).'),
 'pred_factors':('Merkmale dieser Lage, die im ganzen Fallbestand den grössten Unterschied machen','Features of this situation that make the biggest difference across the caseload',
                 'Caractéristiques de cette situation qui font le plus de différence dans l’ensemble des dossiers'),
 'pred_up':('höhere Quoten','higher rates','taux plus élevés'),
 'pred_down':('tiefere Quoten','lower rates','taux plus bas'),
 'pred_model':('Muster aus einer logistischen Regression, auf diesem Rechner trainiert mit {n} abgeschlossenen Fällen (AUC {auc}, Kreuzvalidierung). Ohne Nationalität, Muttersprache und Geschlecht. Keine Bewertung pro Person.',
               'Patterns from a logistic regression trained on this computer with {n} completed cases (AUC {auc}, cross-validated). Nationality, mother tongue and gender are not used. No score per person.',
               'Profils issus d’une régression logistique entraînée sur cet ordinateur avec {n} dossiers terminés (AUC {auc}, validation croisée). Sans nationalité, langue maternelle ni sexe. Aucune note par personne.'),
 'pred_caution':('Gruppenmuster für das Gespräch, keine Aussage über diese Person. Nie für Leistungen oder Sanktionen verwenden.',
                 'Group patterns for the conversation, not a statement about this person. Never use them for benefits or sanctions.',
                 'Profils de groupe pour l’entretien, pas un jugement sur cette personne. Ne jamais les utiliser pour des prestations ou des sanctions.'),
 'help_prediction':('Ein Modell lernt aus Personen, deren A1-Frist abgelaufen ist, welche Merkmale mit Erfolg einhergehen. Angezeigt werden Quoten ähnlicher Gruppen (mindestens 8 Personen), nie eine Zahl für diese Person.',
                    'A model learns from people whose A1 deadline has passed which features go with success. It shows rates for similar groups (at least 8 people), never a number for this person.',
                    'Un modèle apprend, à partir des personnes dont le délai A1 est échu, quelles caractéristiques vont avec la réussite. Il montre des taux de groupes semblables (au moins 8 personnes), jamais un chiffre pour cette personne.'),
 'pv_ai_1':('Gruppenmuster: ein Modell, das auf diesem Rechner trainiert wird und läuft. Es zeigt Quoten ähnlicher Gruppen ab 8 Personen, nie eine Bewertung pro Person. Nationalität, Muttersprache und Geschlecht werden nicht verwendet.',
            'Group patterns: a model trained and run on this computer. It shows rates for similar groups of 8 or more people, never a score per person. Nationality, mother tongue and gender are not used.',
            'Profils de groupe : un modèle entraîné et exécuté sur cet ordinateur. Il montre des taux de groupes semblables d’au moins 8 personnes, jamais une note par personne. Sans nationalité, langue maternelle ni sexe.'),
})

DATASET_NAMES = {'language':'Sprachstand','official':'Integrationszielerreichung','work':'Erwerb',
                 'education':'Integrationsförderung und Ausbildung','membership':'Dossierperson',
                 'support':'Finanzielle Unterstützung','zemis':'ZEMIS Tätigkeit','housing':'Unterbringung',
                 'status':'Asylverfahrensstand'}


def esc(v):
    return escape(str(v if v is not None else '—'),quote=True)


def swiss(value):
    """Swiss date format (dd.mm.yyyy) for dates and ISO strings; anything else is passed through."""
    if isinstance(value,str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime('%d.%m.%Y') if isinstance(value,date) else value


def say(lang,key,**values):
    return esc(tr(lang,key)).format(**{k:esc(v) for k,v in values.items()})


def tip(lang,key):
    # A click-to-open explanation without JavaScript (the CSP allows no scripts).
    return (f'<details class="tip"><summary aria-label="{text(lang,"help_label")}" title="{text(lang,"help_label")}">i</summary>'
            f'<span class="tip-body" role="note">{text(lang,key)}</span></details>')


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
    return f'<span class="badge {esc(state)}"><i aria-hidden="true"></i>{text(lang,state)}</span>'


# Stroke icons drawn on a 24-unit grid; rendered inline so the strict CSP needs no extra sources.
ICONS = {
    'overview':'<rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/>',
    'queue':'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    'reports':'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h8M12 11v8"/>',
    'ai':'<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    'forecast':'<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 6-7"/><path d="M15 7h5v5"/>',
    'intake':'<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 3v2h6V3M9 10h6M9 14h6M9 18h3"/>',
    'ai-analysis':'<path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z"/>',
    'mail':'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    'phone':'<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
    'help':'<circle cx="12" cy="12" r="9"/><path d="M9.5 9.2a2.6 2.6 0 0 1 5 .9c0 1.7-2.5 2.3-2.5 3.9M12 17h.01"/>',
    'privacy':'<path d="M12 3l7 3v5c0 4.6-3 8.3-7 10-4-1.7-7-5.4-7-10V6z"/><rect x="9" y="11" width="6" height="5" rx="1"/><path d="M10 11V9.5a2 2 0 0 1 4 0V11"/>',
    'people':'<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    'homes':'<path d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
    'met':'<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16.5 9.5"/>',
    'follow':'<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
    'calendar':'<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
}


def icon(name,cls='icon'):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[name]}</svg>')


STATE_ORDER = ('achieved','late','ontrack','risk','overdue','review','na')


def state_bar(totals):
    # Proportional SVG bar; the count list beside it carries the same data as text.
    total = sum(totals.values())
    if not total:
        return ''
    x, parts = 0.0, []
    for state in STATE_ORDER:
        width = 100*totals.get(state,0)/total
        if width:
            parts.append(f'<rect class="seg-{state}" x="{x:.3f}" y="0" width="{width:.3f}" height="10"/>')
            x += width
    return f'<svg class="state-bar" viewBox="0 0 100 10" preserveAspectRatio="none" aria-hidden="true" focusable="false">{"".join(parts)}</svg>'


def institutional_marks(lang):
    return (
        f'<section class="institutions" aria-label="{text(lang,"brand_context")}">'
        f'<p>{text(lang,"brand_context")}</p><div class="institutions-row">'
        '<a class="mark city-mark" href="https://www.bern.ch/asylsozialdienst"><img src="/static/stadt-bern-logo.png" alt="Stadt Bern"></a>'
        '<span class="mark canton-mark"><img src="/static/bern-flag.png" alt=""><span><strong>Kanton Bern</strong><small>Canton de Berne</small></span></span>'
        f'<a class="mark sem-mark" href="https://www.sem.admin.ch/"><img src="/static/sem-shield.svg" alt=""><span><strong>SEM</strong><small>{text(lang,"sem_name")}</small></span></a>'
        '<span class="mark swiss-mark"><span class="swiss-flag" aria-hidden="true"></span><span><strong>Schweiz</strong><small>Suisse · Svizzera · Svizra</small></span></span>'
        f'</div><p class="independence">{text(lang,"brand_independence")}</p></section>'
    )


def ai_callout(lang):
    return (f'<section class="callout ai-callout"><span class="ai-badge">{text(lang,"ai_badge")} + Claude</span>'
            f'<p class="callout-text">{text(lang,"ai_analysis_lead")}</p><a class="button" href="/ai-analysis">{icon("ai","icon")}{text(lang,"ai_analysis_open")}</a>{tip(lang,"help_ai_analysis")}</section>')


def menus_for(role):
    menus = ['overview','queue','ai-analysis','reports','ai','forecast','intake']
    if role=='worker':
        menus = [m for m in menus if m not in ('forecast','ai-analysis')]
    if role=='manager':
        menus = [m for m in menus if m not in ('queue','intake')]
    if role=='importer':
        menus = ['reports','intake','ai']
    return menus+['help','privacy']


def layout(lang,active,body,account=None,csrf='',snapshot=None,demo_switch=False,view_path=''):
    menus = menus_for(account['role']) if account else []
    nav = ''.join(f'<div class="nav-row"><a href="/{key}" {"aria-current=page" if key==active or key=="queue" and active=="case" else ""}>{icon(key,"nav-icon")}<span>{text(lang,key)}</span></a>{tip(lang,"help_"+key)}</div>' for key in menus) if account else ''
    target = urlsplit(view_path or '/'+active)
    parameters = parse_qs(target.query)
    filters = {k:parameters[k][0] for k in ('q','state','page','goal','factor','topic','intent','asof') if k in parameters}
    language = ''.join(f'<a lang="{locale}" href="{href(f'/language/{locale}', view=target.path, **filters)}" {"aria-current=page" if i==lang else ""}>{locale[:2].upper()}</a>'
                       for i,locale in enumerate(LOCALES))
    date = f'<span class="snapshot">{icon("calendar")}{text(lang,"snapshot")} <strong>{esc(swiss(snapshot["asof"]))}</strong></span>{tip(lang,"help_snapshot")}' if snapshot else ''
    logout = post('/logout',csrf,action(lang,'logout')+tip(lang,'help_logout')) if account else ''
    persona = ''
    if demo_switch:
        opts = ''.join(f'<option value="{key}" {"selected" if key==account["role"] else ""}>{text(lang,"role_"+key)}</option>'
                       for key in ('judge','worker','manager','importer'))
        persona = post('/demo-role',csrf,f'<label>{text(lang,"demo_persona")} <select name="role">{opts}</select></label>'+action(lang,'apply_role')+tip(lang,'help_persona'))
    role_label = f'<span class="role-label">{text(lang,"role_"+account["role"])}</span>' if account else ''
    frame = (f'<aside><a class="brand" href="/"><img class="brand-mark" src="/static/stadt-bern-shield.png" alt="Stadt Bern"><div>Integrations-Cockpit<small>Bern</small></div></a>'
             f'<nav aria-label="{text(lang,"navigation")}">{nav}</nav><div class="aside-bottom">{role_label}{persona}'
             '<div class="aside-marks" aria-hidden="true"><img src="/static/bern-flag.png" alt=""><img src="/static/sem-shield.svg" alt=""><span class="swiss-flag"></span></div></div></aside>') if account else ''
    mode = 'dashboard' if account else 'signin'
    return f'''<!doctype html><html lang="{LOCALES[lang]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{text(lang,active)} · Integrations-Cockpit Bern</title><link rel="stylesheet" href="/static/app.css"></head>
<body class="{mode}"><a class="skip-link" href="#main">{text(lang,"skip_main")}</a>{frame}<div class="workspace"><header><div class="header-context"><span class="swiss-flag" role="img" aria-label="Schweiz · Suisse · Svizzera"></span>{date or f'<span class="snapshot">{text(lang,"brand_independence")}</span>'}</div><div class="header-actions"><div class="languages">{language}</div>{tip(lang,"help_language")}{logout}</div></header>
<main id="main" tabindex="-1">{body}{institutional_marks(lang)}<footer class="photo-credit">{('<a href="https://commons.wikimedia.org/wiki/File:Bern_Altstadt_von_Rosengarten_20211007.jpg">Bern · Daniel Kraft</a> · <a href="https://creativecommons.org/licenses/by-sa/3.0/">CC BY-SA 3.0</a>' if active in ('overview','login') else '')+(f' · <a href="/privacy">{text(lang,"privacy")}</a>' if not account else '')}</footer></main></div></body></html>'''


def a1_targets(lang,cases,field):
    """Level 1 totals on screen; same partition as the Excel worker / entry-year sheets."""
    groups = {}
    for case in cases:
        value = case[field]
        key = value.year if field=='entry' and value else value
        groups.setdefault(str(key or '—'),[]).append(case)

    def row(label,items):
        scope = [c for c in items if c['goals'][0]['scope']=='scope_in']
        due = [c for c in scope if c['goals'][0].get('due')]
        states = {}
        for c in scope:
            states[c['goals'][0]['state']] = states.get(c['goals'][0]['state'],0)+1
        ontime = sum(c['goals'][0]['state']=='achieved' for c in due)
        late = sum(c['goals'][0]['state']=='late' for c in due)
        missed = sum(c['goals'][0]['state'] in ('overdue','risk') for c in due)
        review = sum(c['goals'][0]['state']=='review' for c in scope)
        rate = f'<strong>{ontime/len(due):.0%}</strong>' if due else '—'
        return (label,state_bar(states),len(scope),len(due),ontime,rate,late,missed,len(scope)-len(due),review)
    rows = [row(esc(key),items) for key,items in sorted(groups.items())]
    rows.append(row(f'<strong>{text(lang,"total")}</strong>',cases))
    headers = [tr(lang,'worker' if field=='worker' else 'year')]+[tr(lang,k) for k in
               ('col_mix','col_scope','col_due','col_ontime','col_rate','col_late','col_missed','col_open','col_review')]
    return table(headers,rows)


def rate_bar(k,n,band):
    rate = 100*k/n
    low, high = 100*band[0], 100*band[1]
    return (f'<svg class="rate-bar" viewBox="0 0 100 14" preserveAspectRatio="none" aria-hidden="true" focusable="false">'
            f'<rect class="track" x="0" y="4" width="100" height="6"/><rect class="rate" x="0" y="4" width="{rate:.2f}" height="6"/>'
            f'<rect class="band" x="{low:.2f}" y="1" width="{high-low:.2f}" height="12"/></svg>')


def insight(lang,public):
    shown = [row for row in public if row[1]]
    if len(shown)<2:
        return ''
    high = max(shown,key=lambda r:r[3]/r[1])
    low = min(shown,key=lambda r:r[3]/r[1])
    sentence = say(lang,'insight',high=tr(lang,high[0]),high_rate=f'{high[3]/high[1]:.0%}',high_n=high[1],
                   low=tr(lang,low[0]),low_rate=f'{low[3]/low[1]:.0%}',low_n=low[1],
                   diff=round(100*(high[3]/high[1]-low[3]/low[1])))
    separate = low[4][1] < high[4][0]
    return f'<p class="insight">{sentence} {text(lang,"insight_clear" if separate else "insight_overlap")}</p>'


def overview(lang,snapshot,cases,management,dimension='year',intake_categories=None,goal_index=0,trend=(),ai_link=False):
    s = rules.counts(cases,0)
    metrics = (('people',len(cases)),('homes',len({c['home'] for c in cases})),('met',s['achieved']),
               ('follow',sum(s[key] for key in ('risk','overdue','review'))))
    if management and snapshot['source']!='synthetic':
        metrics = tuple((key,'—') for key,_ in metrics)
    kpis = ''.join(f'<article class="kpi kpi-{k}">{icon(k,"kpi-icon")}<span>{text(lang,k)}</span><strong>{v}</strong></article>' for k,v in metrics)
    goals = []
    for i,key in enumerate(('a1','work','household')):
        totals = rules.counts(cases,i)
        statuses = [(state,count) for state,count in totals.most_common() if snapshot['source']=='synthetic' or not management]
        rows = ''.join(f'<li>{badge(lang,state)}<strong>{count}</strong></li>' for state,count in statuses)
        bar = state_bar(dict(statuses))
        goals.append(f'<article class="panel goal-card goal-{i+1}"><p class="goal-number">{i+1}</p><h3>{text(lang,key)}</h3>{bar}<ul class="breakdown">{rows}</ul></article>')
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
        rendered = table([tr(lang,'category'),tr(lang,'rate_chart'),'n',tr(lang,'met'),tr(lang,'observed_rate'),tr(lang,'confidence_interval'),tr(lang,'difference')],
          ((text(lang,label),rate_bar(k,n,band) if n else '',esc(n) if n else text(lang,'suppressed'),
            f'<strong>{k/n:.0%}</strong>' if n else '—',f'{observed/n:.0%}' if n else '—',f'{band[0]:.0%}–{band[1]:.0%}' if band else '—',
            f'{(k/n-baseline)*100:+.1f} pp' if n else '—') for label,n,observed,k,band in breakdown))
        finding = insight(lang,public)
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
        targets = (f'<section class="panel targets"><div class="section-head"><h2>{text(lang,"targets_title")}</h2>{tip(lang,"help_targets")}</div>'
                   f'<p>{text(lang,"targets_lead")}</p><h3>{text(lang,"by_worker")}</h3>{a1_targets(lang,cases,"worker")}'
                   f'<h3>{text(lang,"by_year")}</h3>{a1_targets(lang,cases,"entry")}<p class="muted">{text(lang,"targets_note")}</p></section>')
        factor_panel = targets+f'<section class="panel"><div class="section-head"><h2>{text(lang,"level2_title")}</h2>{tip(lang,"help_factor")}</div>{finding}<p class="muted">{text(lang,"synthetic_patterns")}</p><p>{window} · {esc(swiss(snapshot["asof"]))} · {text(lang,"upcoming_due")} {upcoming} · {text(lang,"missing")} {missing}</p><div class="chips">{goal_choices}</div><div class="chips">{choices}</div>{rendered}<p>{text(lang,"analysis_note")}</p><p>{text(lang,"source_limit")}</p><div class="button-row"><a class="button" href="{aggregates}">{text(lang,"safe_aggregates")}</a>{tip(lang,"help_aggregates")}</div></section><section class="panel"><h2>{text(lang,"caseload")}</h2>{caseload}<p>{text(lang,"quality_note")}</p></section>'
    import json
    sources = json.loads(snapshot['inspected'])
    coverage_card = f'<section class="panel"><h2>{text(lang,"coverage_overview")}</h2><dl><dt>{text(lang,"sources_present")}</dt><dd>{len(sources)}</dd><dt>{text(lang,"nonempty_sources")}</dt><dd>{sum(n>0 for n in sources.values())}</dd></dl><a href="/reports">{text(lang,"reports")}</a></section>'
    trend_card = ''
    if trend:
        rows = ((esc(swiss(d)),esc(n),esc(k),f'{k/n:.1%}' if n else text(lang,'suppressed')) for d,n,k in trend)
        trend_card = f'<section class="panel"><h2>{text(lang,"trend")}</h2>'+table(
            [tr(lang,'snapshot'),tr(lang,'scope_in'),tr(lang,'met'),'%'],rows)+'</section>'
    return f'''<section class="hero"><img class="bern-image" src="/static/bern.jpg" alt=""><div class="hero-copy"><p class="eyebrow">{text(lang,'demo' if snapshot['source']=='synthetic' else 'local')}</p>
{heading(lang,'overview',text(lang,'lead'))}</div></section>
{ai_callout(lang) if ai_link else ''}<div class="kpis">{kpis}</div><h2>{text(lang,'goals')}</h2><div class="three">{''.join(goals)}</div><div class="two">{coverage_card}{trend_card}</div>
{factor_panel}'''


def analysis_export(lang,snapshot,cases,dimension,intake_categories,goal_index):
    from datetime import date
    asof = date.fromisoformat(snapshot['asof'])
    rows,coverage,_ = rules.analysis(cases,asof,dimension,intake_categories,goal_index)
    return {
        tr(lang,'sheet_metadata'): [[tr(lang,'field'),tr(lang,'value')],[tr(lang,'snapshot'),asof],[tr(lang,'source'),tr(lang,'demo')],
                     [tr(lang,'goals'),tr(lang,('a1','work','household')[goal_index])],
                     [tr(lang,'category'),tr(lang,dimension if goal_index==0 else 'cutoff_year')],
                     [tr(lang,'upcoming_due'),coverage.get('upcoming')],[tr(lang,'missing'),coverage.get('missing')]],
        tr(lang,'sheet_aggregates'): [[tr(lang,'category'),'n',tr(lang,'a1_attainment') if goal_index==0 else tr(lang,'attained'),
                       tr(lang,'met'),tr(lang,'ci_lower'),tr(lang,'ci_upper')]] +
                      [[tr(lang,label),n,observed,k,*(band or (None,None))] for label,n,observed,k,band in rows],
    }


LIGHT_SYMBOLS = {'achieved':'✓','late':'!','ontrack':'→','risk':'!','overdue':'!','review':'?','na':'–'}


def lights(lang,case):
    # One traffic light per goal; colour, symbol and a text label so meaning never depends on colour alone.
    return '<span class="lights">'+''.join(
        f'<span class="light {esc(g["state"])}" title="{text(lang,key)}: {text(lang,g["state"])}">'
        f'<i aria-hidden="true">{LIGHT_SYMBOLS[g["state"]]}</i><span class="visually-hidden">{text(lang,key)}: {text(lang,g["state"])}</span></span>'
        for key,g in zip(('a1','work','household'),case['goals']))+'</span>'


def when_label(lang,action):
    if action['when'] is None:
        return '—'
    days = action['days']
    relative = text(lang,'today') if days==0 else say(lang,'in_days',n=days) if days>0 else say(lang,'days_ago',n=-days)
    return f'<span class="when"><strong>{swiss(action["when"])}</strong><small>{relative}</small></span>'


def action_label(lang,action):
    goal = tr(lang,('a1','work','household')[action['goal']]) if action['goal'] is not None else ''
    return say(lang,action['key'],date=swiss(action['when']),days=abs(action['days'] or 0),goal=goal)


def unrecorded(case):
    """A goal reached on time whose official record is missing or carries another date."""
    return any(g['state']=='achieved' and (g.get('official_undated') or set(g.get('official_dates',()))!={g['achieved']})
               for g in case['goals'])


def queue(lang,cases,query,page,filter_state,asof):
    planned = [(c,rules.next_action(c,asof)) for c in cases if query.casefold() in c['id'].casefold()]
    week = [(c,a) for c,a in planned if a['week']]
    if filter_state=='week':
        planned = week
    elif filter_state=='zemis':
        planned = [(c,a) for c,a in planned if c['zemis_findings']]
    elif filter_state=='record':
        planned = [(c,a) for c,a in planned if unrecorded(c)]
    elif filter_state:
        planned = [(c,a) for c,a in planned if c['goals'][0]['state']==filter_state]
    order = lambda item:(item[1]['rank'],str(item[1]['when'] or '9999'),item[0]['id'])
    planned.sort(key=order)
    week.sort(key=order)
    offset = (page-1)*20
    states = ('week','record','zemis','overdue','risk','review','ontrack','late','achieved','na')
    options = ''.join(f'<option value="{key}" {"selected" if key==filter_state else ""}>{text(lang,key)}</option>' for key in states)
    form = f'''<form class="inline" action="/queue"><label>{text(lang,'search')} <input name="q" value="{esc(query)}"></label>
<label>{text(lang,'status_filter')} · {text(lang,'a1')} <select name="state"><option value="">{text(lang,'all_statuses')}</option>{options}</select></label>{action(lang,'search')}{tip(lang,'help_search')}<a class="chip" href="/queue">{text(lang,'reset_filters')}</a>{tip(lang,'help_reset')}</form>'''
    spotlight = ''
    if not query and not filter_state and page==1 and week:
        items = ''.join(f'''<li><div class="week-head"><a class="case-link" href="/case/{quote(c["id"],safe="")}">{esc(c["id"])}</a>{lights(lang,c)}<span class="worker">{esc(c["worker"])}</span></div>
<p>{action_label(lang,a)}</p>{when_label(lang,a)}</li>''' for c,a in week[:6])
        spotlight = (f'<section class="panel week"><div class="section-head"><h2>{text(lang,"this_week")}</h2>{tip(lang,"help_week")}</div>'
                     f'<p>{say(lang,"this_week_note",n=len(week))}</p><ol class="week-list">{items}</ol>'
                     f'<a class="button" href="{href("/queue",state="week")}">{say(lang,"show_all_week",n=len(week))}</a></section>')
    rows = ((f'<a class="case-link" href="/case/{quote(c["id"],safe="")}">{esc(c["id"])}</a>',lights(lang,c),
             action_label(lang,a),when_label(lang,a),esc(c['worker']))
            for c,a in planned[offset:offset+20])
    pagination = '<div class="pagination">'
    if page>1:
        pagination += f'<a href="{href("/queue",q=query,state=filter_state,page=page-1)}">{text(lang,"previous")}</a>'
    if offset+20<len(planned):
        pagination += f'<a href="{href("/queue",q=query,state=filter_state,page=page+1)}">{text(lang,"next")}</a>'
    count = f'<p class="result-count">{text(lang,"queue_count")} · {len(planned)} · {text(lang,"page_number")} {page}</p>'
    legend = f'<p class="legend">{text(lang,"ampel_legend")}</p>'
    head = heading(lang,'queue',text(lang,'queue_lead'))+spotlight+f'<div class="section-head"><h2>{text(lang,"all_cases")}</h2>{tip(lang,"help_case_link")}</div>'+form+legend+count
    if not planned[offset:offset+20]:
        return head+f'<section class="panel"><p>{text(lang,"empty_queue")}</p></section>'+pagination+'</div>'
    return head+table([tr(lang,'case_identifier'),tr(lang,'lights_header'),tr(lang,'next_step'),tr(lang,'when'),tr(lang,'worker')],rows)+pagination+'</div>'


def source_row(case,dataset,line):
    for rows in (case['tables'].get(dataset) or (),case['household'].get(dataset) or ()):
        for row in rows:
            if row['_line']==line:
                return row
    return None


def describe(lang,dataset,row):
    # Source values stay verbatim (German), only dates are shown in Swiss format.
    v = lambda key: row.get(key)
    span = lambda a,b: f'{swiss(v(a)) or "—"} – {swiss(v(b)) if v(b) else tr(lang,"open")}'
    parts = {
        'language':(v('Sprache'),v('Sprachniveau'),v('Art'),v('Bemerkungen'),swiss(v('Datum Erreichung'))),
        'official':(v('Art'),swiss(v('Erreicht am')),v('Partner')),
        'work':(v('Arbeitgeber Name'),f'{v("Pensum %")} %' if v('Pensum %') is not None else None,v('Erwerbsstatus'),span('Von','Bis'),v('Bemerkungen')),
        'education':(v('Art'),v('Bezeichnung'),v('Institution Name'),span('Start','Abschluss')),
        'membership':(v('Beziehung'),v('Rolle'),span('Dossierperson Von','Dossierperson Bis')),
        'support':(v('Unterstützung'),span('Finanzielle Unterstützung Gültig von','Finanzielle Unterstützung Gültig bis'),v('Hauptgrund Beendigung Unterstützung')),
    }.get(dataset,())
    return ' · '.join(esc(p) for p in parts if p not in (None,''))


def explain(lang,goal,asof):
    deadline, achieved = goal['deadline'], goal['achieved']
    days = abs((deadline-asof).days) if deadline else 0
    key = 'exp_'+goal['state']
    if goal['state'] in ('review','na') or not deadline:
        return say(lang,'exp_na' if goal['state']=='na' else 'exp_review',reason=tr(lang,goal['reason']))
    sentence = say(lang,key,deadline=swiss(deadline),achieved=swiss(achieved),days=days)
    if goal['state'] in ('achieved','late'):
        dates = ', '.join(swiss(d) for d in goal.get('official_dates',()))
        sentence += ' '+(say(lang,'exp_official_yes',dates=dates) if dates else text(lang,'exp_official_no'))
    return sentence


def detail(lang,case,asof,prediction=None,contact=None):
    step = rules.next_action(case,asof)
    facts = [(tr(lang,'worker'),case['worker']),(tr(lang,'status_label'),case['status']),(tr(lang,'entry_date'),swiss(case['entry'])),
             (tr(lang,'age_label'),case['age']),(tr(lang,'household_id'),case['home'])]
    summary = ''.join(f'<div><span>{esc(k)}</span><strong>{esc(v)}</strong></div>' for k,v in facts)
    callout = (f'<section class="callout {"urgent" if step["week"] else ""}"><p class="eyebrow-dark">{text(lang,"next_step")}</p>'
               f'<p class="callout-text">{action_label(lang,step)}</p>{when_label(lang,step)}</section>')
    sections = []
    for key,g in zip(('a1','work','household'),case['goals']):
        rows = [(tr(lang,'deadline'),swiss(g['deadline'])),(tr(lang,'attained'),swiss(g['achieved'])),(tr(lang,'scenario'),swiss(g['earliest']))]
        if key=='a1':
            due_key = {True:'due_now',False:'upcoming_due',None:'due_unknown'}[g.get('due')]
            rows.extend([(tr(lang,'scope'),tr(lang,g['scope'])),(tr(lang,'entry_date'),swiss(case['entry'])),
                         (tr(lang,'due_status'),tr(lang,due_key) if g['scope']=='scope_in' else None)])
        elif key=='work':
            rows.extend((tr(lang,label),swiss(case[field])) for label,field in (
                ('baseline_end','end'),('reference_end','reference_end'),('transition_end','transition_end')))
        else:
            rows.append((tr(lang,'period_start'),swiss(g.get('period_start'))))
        facts_list = ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v)}</dd>' for k,v in rows)
        evidence = []
        for dataset,line in g['evidence']:
            row = source_row(case,dataset,line)
            body = describe(lang,dataset,row) if row else ''
            evidence.append(f'<li><span class="source-tag">{esc(DATASET_NAMES.get(dataset,dataset))} · {text(lang,"row")} {esc(line)}</span>{body}</li>')
        evidence_html = f'<ul class="evidence">{"".join(evidence)}</ul>' if evidence else f'<p class="muted">{text(lang,"no_evidence")}</p>'
        sections.append(f'''<section class="panel goal-detail"><h2>{text(lang,key)}</h2>{badge(lang,g["state"])}
<p class="reason">{text(lang,g["reason"])}</p><div class="explain"><h3>{text(lang,"what_means")}</h3><p>{explain(lang,g,asof)}</p></div>
<h3>{text(lang,"evidence_rows")}</h3>{evidence_html}<details><summary>{text(lang,"deadline")} · {text(lang,"policy")}</summary><dl>{facts_list}</dl></details></section>''')
    timeline = []
    for dataset, label, start, end, fact in (
        ('work','work','Von','Bis','Erwerbsstatus'),('education','education','Start','Abschluss','Art'),
        ('housing','housing','Unterbringung Von','Unterbringung Bis','Unterbringung Art'),
        ('status','status','Verfahrensstand Gültig ab','Verfahrensstand Gültig bis','Verfahrensstand')):
        for record in case['tables'][dataset][:20]:
            timeline.append((record.get(start) or '',record.get(end),label,record.get(fact)))
    rows = table([tr(lang,'source'),tr(lang,'category'),tr(lang,'deadline'),tr(lang,'date_until')],
        ((esc(DATASET_NAMES[label]),esc(value),esc(swiss(a)),esc(swiss(b))) for a,b,label,value in sorted(timeline,key=lambda row:row[0],reverse=True)))
    quality = ''
    if case['zemis_findings']:
        def zemis_label(line):
            row = source_row(case,'zemis',line) or {}
            return say(lang,'zemis_job',company=row.get('Betrieb'),date=swiss(row.get('Arbeitsbeginn')))
        findings = table(['ZEMIS',tr(lang,'result'),tr(lang,'evidence')],
                         ((zemis_label(line),text(lang,reason),esc(', '.join(f'Erwerb {tr(lang,"row")} {r}' for r in rows) or '—'))
                          for line,reason,rows in case['zemis_findings']))
        quality = f'<section class="panel"><h2>{text(lang,"quality")}</h2>{findings}</section>'
    back = f'<div class="back-row"><a class="chip back-link" href="/queue">{text(lang,"back_queue")}</a>{tip(lang,"help_back")}</div>'
    return (heading(lang,'case',esc(case['id']))+back+f'<div class="case-summary">{summary}</div>'+callout+
            f'<div class="two assist">{prediction_panel(lang,case,prediction)}{contact_panel(lang,case,contact,step) if contact else ""}</div>'+
            f'<p class="legend">{text(lang,"ampel_legend")}</p><div class="three">'+''.join(sections)+
            f'</div><section class="panel"><h2>{text(lang,"timeline")}</h2>{rows}</section>{quality}')



def percent(value):
    return f'{round(value*100)} %'


def factor_label(lang,name,case,raw_value):
    person = case['tables']['clients'][0] if case['tables']['clients'] else {}
    if name=='school_years':
        return say(lang,'f_school_years',v=person.get('Schuljahre vor Einreise') if person.get('Schuljahre vor Einreise') is not None else '–')
    if name=='age_at_entry':
        born = rules.as_date(person.get('Geburtsdatum'))
        return say(lang,'f_age_at_entry',v=rules.age_on(born,case['entry']) if born and case['entry'] else '–')
    return text(lang,'f_'+name+('' if raw_value else '_no'))


def prediction_panel(lang,case,result):
    # Group patterns only: the challenge asks for "patterns on groups, never a score per person".
    head = (f'<div class="section-head"><h2>{text(lang,"pred_title")}</h2><span class="ai-badge">{text(lang,"ai_badge")}</span>'
            f'{tip(lang,"help_prediction")}</div>')
    if result is None:
        return f'<section class="panel ai-panel">{head}<p class="muted">{text(lang,"pred_none")}</p></section>'
    if result['peers'] is None:
        figure = f'<p class="muted">{text(lang,"pred_small")}</p>'
    else:
        n,k = result['peers']
        rate = k/n
        tone = 'high' if rate>=.6 else 'mid' if rate>=.35 else 'low'
        bar = (f'<svg class="pred-bar" viewBox="0 0 100 8" preserveAspectRatio="none" aria-hidden="true"><rect class="track" width="100" height="8" rx="4"/>'
               f'<rect class="fill {tone}" width="{max(2,round(rate*100))}" height="8" rx="4"/><rect class="base" x="{round(result["base"]*100)}" width="0.8" height="8"/></svg>')
        figure = (f'<div class="pred-figure"><strong class="{tone}">{percent(rate)}</strong><span>{say(lang,"pred_peers",n=n,k=k)}</span></div>{bar}'
                  f'<p class="legend">{say(lang,"pred_base",rate=percent(result["base"]))}</p>')
    raw = result['raw']
    items = ''.join(f'<li class="{"up" if effect>0 else "down"}"><span>{"▲" if effect>0 else "▼"}</span>{factor_label(lang,name,case,raw.get(name))}'
                    f' <em>{text(lang,"pred_up" if effect>0 else "pred_down")}</em></li>' for name,effect in result['factors'])
    scenario = ''
    if result['scenario'] and result['scenario'][1]:
        key,(n,k) = result['scenario']
        scenario = f'<p class="pred-scenario">{say(lang,key,rate=percent(k/n),n=n)}</p>'
    v = result['validation']
    model = say(lang,'pred_model',n=v['n'],auc=f'{v["auc"]:.2f}',skill=percent(v['skill']))
    return (f'<section class="panel ai-panel">{head}<p>{text(lang,"pred_lead")}</p>{figure}{scenario}'
            f'<h3>{text(lang,"pred_factors")}</h3><ul class="pred-factors">{items}</ul>'
            f'<p class="legend">{model}</p><p class="legend caution">{text(lang,"pred_caution")}</p></section>')


MAIL = {
 'mail_a1':(('Anmeldung zur A1-Prüfung','Registering for the A1 exam','Inscription à l’examen A1'),
            ('Guten Tag\n\nIhre Frist für den Nachweis Deutsch A1 endet am {date}. Gerne unterstütze ich Sie bei der Anmeldung zu einer fide- oder telc-Prüfung. Bitte melden Sie sich bei mir für einen Termin.\n\nFreundliche Grüsse\n{worker}\nAsylsozialdienst Stadt Bern',
             'Hello\n\nYour deadline for German A1 proof is {date}. I would be glad to help you register for a fide or telc exam. Please contact me to arrange an appointment.\n\nKind regards\n{worker}\nAsylum Social Service, City of Bern',
             'Bonjour\n\nVotre délai pour prouver le niveau A1 en allemand est le {date}. Je vous aide volontiers à vous inscrire à un examen fide ou telc. Merci de me contacter pour fixer un rendez-vous.\n\nMeilleures salutations\n{worker}\nService social de l’asile, Ville de Berne')),
 'mail_meeting':(('Termin beim Asylsozialdienst','Appointment at the Asylum Social Service','Rendez-vous au Service social de l’asile'),
            ('Guten Tag\n\nIch möchte mit Ihnen die nächsten Schritte besprechen: Deutsch, Arbeit oder Ausbildung. Bitte rufen Sie mich an oder antworten Sie auf diese E-Mail, damit wir einen Termin finden.\n\nFreundliche Grüsse\n{worker}\nAsylsozialdienst Stadt Bern',
             'Hello\n\nI would like to discuss the next steps with you: German, work or education. Please call me or reply to this email so we can find a time to meet.\n\nKind regards\n{worker}\nAsylum Social Service, City of Bern',
             'Bonjour\n\nJ’aimerais discuter avec vous des prochaines étapes : allemand, travail ou formation. Merci de m’appeler ou de répondre à cet e-mail pour fixer un rendez-vous.\n\nMeilleures salutations\n{worker}\nService social de l’asile, Ville de Berne')),
 'mail_documents':(('Unterlagen für Ihr Dossier','Documents for your file','Documents pour votre dossier'),
            ('Guten Tag\n\nFür Ihr Dossier fehlt noch ein Nachweis, zum Beispiel ein Sprachzertifikat oder ein Arbeitsvertrag. Bitte bringen Sie das Dokument zum nächsten Termin mit oder senden Sie mir eine Kopie.\n\nFreundliche Grüsse\n{worker}\nAsylsozialdienst Stadt Bern',
             'Hello\n\nYour file is still missing a document, for example a language certificate or an employment contract. Please bring it to your next appointment or send me a copy.\n\nKind regards\n{worker}\nAsylum Social Service, City of Bern',
             'Bonjour\n\nIl manque encore un justificatif dans votre dossier, par exemple un certificat de langue ou un contrat de travail. Merci de l’apporter au prochain rendez-vous ou de m’en envoyer une copie.\n\nMeilleures salutations\n{worker}\nService social de l’asile, Ville de Berne')),
}
MAIL_FOR = {'act_g1_risk':'mail_a1','act_g1_plan':'mail_a1','act_g1_verify':'mail_documents','act_g2_verify':'mail_documents','act_zemis':'mail_documents'}


def demo_contact(case):
    number = int(''.join(ch for ch in case['id'] if ch.isdigit()) or 0)
    return {'phone':f'+41 79 555 {number//100%100:02d} {number%100:02d}','email':f'{case["id"].lower()}@example.org'}


def contact_panel(lang,case,contact,step):
    suggested = MAIL_FOR.get(step['key'],'mail_meeting')
    deadline = swiss(case['goals'][0].get('deadline')) or '—'
    def mail_links(key):
        (subjects,bodies) = MAIL[key]
        links = ''.join(f'<a class="button{"" if i==lang else " secondary"}" href="mailto:{quote(contact["email"])}?subject={quote(subjects[i])}&amp;body={quote(bodies[i].format(date=deadline,worker=case["worker"]))}">'
                        f'{icon("mail","icon")}{text(lang,"write_mail")} · {code}</a>' for i,code in enumerate(('DE','EN','FR')))
        preview = esc(bodies[lang].format(date=deadline,worker=case['worker']))
        return (f'<div class="mail-template"><h3>{text(lang,key)}</h3><div class="mail-actions">{links}</div>'
                f'<details><summary>{text(lang,"mail_preview")}</summary><pre class="mail-body">{esc(subjects[lang])}\n\n{preview}</pre></details></div>')
    others = ''.join(mail_links(k) for k in MAIL if k!=suggested)
    phone = contact['phone']
    return (f'<section class="panel contact-panel"><div class="section-head"><h2>{text(lang,"contact_title")}</h2>{tip(lang,"help_contact")}</div>'
            f'<div class="contact-row"><a class="button call" href="tel:{phone.replace(" ","")}">{icon("phone","icon")}{text(lang,"call")} · {esc(phone)}</a>'
            f'<a class="contact-mail" href="mailto:{quote(contact["email"])}">{esc(contact["email"])}</a></div>'
            f'<p class="eyebrow-dark">{text(lang,"mail_suggested")}</p>{mail_links(suggested)}'
            f'<details class="more-templates"><summary>{text(lang,"mail_other")}</summary>{others}</details>'
            f'<p class="legend">{text(lang,"contact_demo")}</p></section>')


def shield_panel(lang,report):
    labels = {'ahv':'AHV','iban':'IBAN','email':'E-Mail','phone':'Tel.','case_id':'ID / ZEMIS','number':'Nr.','date':'Datum','address':'Adresse','name':'Name'}
    chips = ''.join(f'<span class="shield-chip">{esc(labels[k])} · {n}</span>' for k,n in sorted(report['masked'].items()))
    found = f'<p><strong>{text(lang,"shield_hidden")}:</strong> {chips}</p>' if chips else f'<p>{text(lang,"shield_none")}</p>'
    sent = esc(report['sent'][:4000])
    marked = sent
    for label in ('[NAME]','[DATUM]','[AHV]','[ADRESSE]','[TELEFON]','[E-MAIL]','[IBAN]','[ID]','[NUMMER]'):
        marked = marked.replace(label,f'<mark>{label}</mark>')
    return (f'<section class="panel shield"><div class="section-head"><h2>{icon("privacy","icon")}{text(lang,"shield_title")}</h2></div>'
            f'<p>{text(lang,"shield_lead")}</p>{found}<details open><summary>{text(lang,"shield_sent")}</summary><pre class="shield-text">{marked}</pre></details></section>')


def ai_state(lang,report):
    state = report['state']
    if state in ('off','missing_sdk','answered','blocked'):
        return f'<p class="ai-state {state}">{text(lang,"ai_state_"+state)}</p>'
    return f'<p class="ai-state error">{say(lang,"ai_state_error",state=state)}</p>'


def ai_answer(lang,answer,report,local_lines):
    if answer:
        body = ''.join(f'<p>{esc(line)}</p>' for line in answer.split('\n') if line.strip())
        title = text(lang,'ai_summary')
    else:
        body = '<ul class="plain">'+''.join(f'<li>{line}</li>' for line in local_lines)+'</ul>'
        title = text(lang,'ai_local_summary')
    return f'<div class="ai-answer"><h3>{icon("ai","icon")}{title}</h3>{body}</div>{ai_state(lang,report)}'


def due_outcomes(cases):
    """People whose A1 deadline has passed, and how many of them reached A1 on time."""
    due = [c for c in cases if c['goals'][0].get('due') and c['goals'][0]['state'] in ('achieved','late','overdue')]
    return len(due),sum(c['goals'][0]['state']=='achieved' for c in due)


def analysis_material(cases,asof,model):
    """Aggregate-only text for the language model: totals and unsuppressed group rates, no case rows."""
    totals = dict(zip(rules.A1_TOTALS,rules.a1_totals(cases)))
    lines = [f'Stichtag Ende {asof.month:02d}/{asof.year}. Personen {totals["people"]}, im Geltungsbereich A1 {totals["scope_in"]}.',
             'Ziel 1 (A1 in 3 Jahren): Frist abgelaufen {}, davon fristgerecht {}, verspätet {}, verpasst {}.'.format(*due_outcomes(cases),totals['late'],totals['overdue'])]
    for i,key in enumerate(('Ziel 1 Sprache','Ziel 2 Arbeit/Ausbildung','Ziel 3 Finanzielle Selbstständigkeit')):
        lines.append(f'{key}: '+', '.join(f'{state} {n}' for state,n in sorted(rules.counts(cases,i).items())))
    for dimension in ('course','age','schooling','year'):
        rows,_,_ = rules.analysis(cases,asof,dimension)
        shown = [(label,n,k/n) for label,n,observed,k,band in rows if k is not None and n]
        if shown:
            lines.append(f'A1 fristgerecht nach {dimension}: '+'; '.join(f'{label} {round(rate*100)}% (n={n})' for label,n,rate in shown))
    lines.append(f'Erreichte Ziele ohne offiziellen Eintrag: {sum(u for _,u,_ in rules.payments(cases))}.')
    lines.append(f'Personen, deren ZEMIS-Meldung nicht zu Erwerb passt: {sum(1 for c in cases if c["zemis_findings"])}.')
    if model.ready:
        lines.append(f'Lokales Prognosemodell A1: AUC {model.validation["auc"]:.2f}, n={model.validation["n"]}; Gewichte '
                     +', '.join(f'{name} {w:+.2f}' for name,w in zip(('Kurs früh','Kurs spät','Schuljahre','Alter bei Einreise','lateinisch alphabetisiert','Kleinkind'),model.weights[1:])))
    return '\n'.join(lines)


def local_analysis(lang,cases,asof):
    lines = []
    due,met = due_outcomes(cases)
    if due:
        lines.append(say(lang,'local_obs_target',met=met,due=due,rate=percent(met/due)))
    rows,_,_ = rules.analysis(cases,asof,'course')
    shown = [(label,k/n) for label,n,observed,k,band in rows if k is not None and n]
    if len(shown)>=2:
        high,low = max(shown,key=lambda r:r[1]),min(shown,key=lambda r:r[1])
        lines.append(say(lang,'local_obs_course',high=tr(lang,high[0]),high_rate=percent(high[1]),low=tr(lang,low[0]),low_rate=percent(low[1])))
    risk = rules.counts(cases,0).get('risk',0)
    if risk:
        lines.append(say(lang,'local_obs_risk',n=risk))
    pending = sum(u for _,u,_ in rules.payments(cases))
    if pending:
        lines.append(say(lang,'local_obs_record',n=pending))
    lines += [text(lang,'local_rec_course'),text(lang,'local_rec_record')]
    return lines


def ai_analysis_page(lang,answer,report,local_lines):
    return (heading(lang,'ai_analysis',text(lang,'ai_analysis_lead'))+
            f'<section class="panel ai-panel"><div class="section-head"><h2>{text(lang,"ai_analysis")}</h2><span class="ai-badge">Claude</span>{tip(lang,"help_ai_analysis")}</div>'
            f'{ai_answer(lang,answer,report,local_lines)}<a class="button secondary" href="/ai-analysis?refresh=1">{text(lang,"ai_refresh")}</a></section>'
            +shield_panel(lang,report))


def reports(lang,snapshot,history,role,csrf,hosted,notice='',issues=(),manifest=()):
    report = f'<span class="button-row"><a class="button" href="/export">{text(lang,"export")}</a>{tip(lang,"help_export")}</span>' if role!='importer' and snapshot else ''
    import_controls = ''
    if role in ('judge','importer'):
        button = action(lang,'synthetic_load')
        options = ''.join(f'<option>{d}</option>' for d in MONTHS)
        exercise = options+f'<option value="{PHASE4_MONTH}">{PHASE4_MONTH} · {text(lang,"phase4_fixture")}</option>'
        exercise += f'<option value="{PHASE5_MONTH}">{PHASE5_MONTH} · {text(lang,"phase5_fixture")}</option>'
        import_controls = post('/seed',csrf,f'<label>{text(lang,"snapshot")} <select name="date">{exercise}</select></label>{button}{tip(lang,"help_seed")}')
        import_controls += post('/seed-invalid',csrf,
            f'<label>{text(lang,"snapshot")} <select name="date">{options}</select></label>'+action(lang,'invalid_demo')+tip(lang,'help_invalid'))
        report += f'<span class="button-row"><a class="button" href="/quality">{text(lang,"quality_export")}</a>{tip(lang,"help_quality")}</span>'
        if not hosted:
            import_controls += post('/import',csrf,
                f'<label>{text(lang,"snapshot")} <input name="date" type="date" required></label>'
                f'<label>Excel <input name="workbooks" type="file" accept=".xlsx" multiple required></label>{action(lang,"import")}{tip(lang,"help_upload")}',True)
    current = ''
    if snapshot:
        import json
        counts = json.loads(snapshot['inspected'])
        current = table([tr(lang,'source'),tr(lang,'rows')],((esc(k),esc(n)) for k,n in counts.items()))
        if manifest:
            records = table([tr(lang,'source'),tr(lang,'fingerprint')],
                            ((esc(r['dataset']),'<code>'+esc(r['sha256'])+'</code>') for r in manifest))
            current += f'<details><summary>{text(lang,"fingerprint")}</summary>{records}</details>{tip(lang,"help_fingerprint")}'
    choices = ''.join(f'<option value="{r["id"]}">{esc(r["asof"])} · {text(lang,"demo" if r["source"]=="synthetic" else "local")}</option>' for r in history)
    history_form = post('/snapshot',csrf,f'<label>{text(lang,"snapshot")} <select name="id">{choices}</select></label>{action(lang,"choose")}{tip(lang,"help_choose_snapshot")}') if choices else ''
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
        tr(lang,'sheet_import'): [[tr(lang,'field'),tr(lang,'value')],[tr(lang,'snapshot'),date.fromisoformat(snapshot['asof']) if snapshot else None],
                   [tr(lang,'source'),tr(lang,'demo' if snapshot['source']=='synthetic' else 'local') if snapshot else None],
                   [tr(lang,'import_attempt'),date.fromisoformat(diagnostic['report_date']) if diagnostic and diagnostic['report_date'] else None],
                   [tr(lang,'result'),tr(lang,status[diagnostic['outcome']]) if diagnostic else None]],
        tr(lang,'sheet_sources'): [[tr(lang,'source'),tr(lang,'rows'),tr(lang,'fingerprint')]] +
                   [[k,n,hashes.get(k)] for k,n in counts.items()],
        tr(lang,'sheet_issues'): [[tr(lang,'source'),tr(lang,'row_number'),tr(lang,'result'),'Code']] +
                  [[key,line,tr(lang,reason),reason] for key,line,reason in issues],
    }


def assistant(lang,topic,result,aggregate,intent='entry_cohort',asof=RULE_DATES[0]):
    topics = ''.join(f'<a class="chip" href="{href("/ai",topic=k,intent=intent,asof=asof)}" {"aria-current=page" if k==topic else ""}>{text(lang,k)}</a>' for k in SOURCES)
    dates = ''.join(f'<option {"selected" if d==asof else ""}>{esc(d)}</option>' for d in RULE_DATES)
    date_picker = f'<form action="/ai"><input type="hidden" name="topic" value="{esc(topic)}"><input type="hidden" name="intent" value="{esc(intent)}"><label>{text(lang,"rule_date")} <select name="asof">{dates}</select></label>{action(lang,"choose")}{tip(lang,"help_rule_date")}</form>'
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
        aggregate_body = f'<div class="chips">{intents}{tip(lang,"help_intents")}</div>{presentation}<p>{text(lang,"group_note")}</p>'
    return heading(lang,'ai',text(lang,'retrieval'))+f'''
<div class="chips">{topics}{tip(lang,"help_topics")}</div><section class="panel reading"><h2>{text(lang,topic)}</h2>{date_picker}{answer}</section>
<div class="two"><section class="panel"><h2>{text(lang,'privacy')}</h2><dl>
<dt>{text(lang,'before')}</dt><dd><code>DEMO-00001 · 08.04.1987 · A1</code></dd>
<dt>{text(lang,'after')}</dt><dd><code>{{"topic": "{esc(topic)}", "locale": "{LOCALES[lang]}", "asof": "{esc(asof)}"}}</code></dd></dl><p>{text(lang,'local_release')}</p></section>
<section class="panel"><h2>{text(lang,'explorer')}</h2>{aggregate_body}</section></div>'''


def figures(items):
    return '<div class="figures">'+''.join(f'<div class="figure"><strong>{esc(v)}</strong><span>{label}</span></div>' for v,label in items)+'</div>'


def chf(amount):
    return 'CHF '+f'{amount:,}'.replace(',','’')


def forecast(lang,report,tariffs,cases,series=None,can_upload=False,csrf='',candidate=None,can_queue=False):
    sections = [('payments','pay_title'),('zemis','zemis_title'),('arrivals','arrivals_title')]
    if candidate is not None:
        sections.insert(1,('scenario','scenario2027'))
    jump = ('<nav class="chips jump" aria-label="'+text(lang,'forecast')+'">'+''.join(f'<a class="chip" href="#{anchor}">{text(lang,key)}</a>' for anchor,key in sections)
            +'</nav>'+tip(lang,'help_jump'))

    summary = rules.payments(cases)
    payment_rows = []
    for key,tariff,(verified,unconfirmed,review) in zip(('a1','work','household'),tariffs,summary,strict=True):
        payment_rows.append((text(lang,key),esc(verified),esc(unconfirmed),esc(review),
                             f'<input type="number" aria-label="{text(lang,key)} · {text(lang,"rate_chf")}" name="rate_{key}" min="0" max="100000" value="{tariff}">',
                             chf(verified*tariff)))
    payable = sum(v*t for (v,_,_),t in zip(summary,tariffs))
    pending = sum(u for _,u,_ in summary)
    payment_rows.append((f'<strong>{text(lang,"pay_total")}</strong>',esc(sum(v for v,_,_ in summary)),esc(pending),
                         esc(sum(r for *_,r in summary)),'',f'<strong>{chf(payable)}</strong>'))
    pricing = table([tr(lang,k) for k in ('goals','verified_attainment','uncorroborated','review','rate_chf','amount_chf')],payment_rows)
    open_note = ''
    if pending:
        missing = sum(u*t for (_,u,_),t in zip(summary,tariffs))
        open_note = (say(lang,'pay_open',n=pending,amount=chf(missing)) if any(tariffs) else say(lang,'pay_open_count',n=pending))
        link = f'<a class="button" href="{href("/queue",state="record")}">{text(lang,"pay_open_link")}</a>' if can_queue else ''
        open_note = f'<div class="callout"><p class="callout-text">{open_note}</p>{link}</div>'
    payments = (f'<section class="panel" id="payments"><div class="section-head"><h2>{text(lang,"pay_title")}</h2>{tip(lang,"help_pricing")}</div>'
                f'<p>{text(lang,"pay_lead")}</p>{open_note}<form class="pricing" action="/forecast">{pricing}{action(lang,"calculate")}</form>'
                f'<p class="legend">{text(lang,"payment_note")}</p></section>')

    scenario = ''
    if candidate is not None:
        changed = sum(a['end']!=b['effective_end'] for a,b in zip(cases,candidate,strict=True))
        inherited = sum(b['entry'] is None and b['effective_end']!=a['end'] for a,b in zip(cases,candidate,strict=True))
        scenario_rows = []
        overdue = risk = 0
        for i,key in enumerate(('a1','work','household')):
            baseline,before = rules.counts(cases,i),rules.counts(candidate,i)
            overdue += before['overdue']-baseline['overdue']
            risk += before['risk']-baseline['risk']
            for state in ('achieved','review','overdue','ontrack','risk'):
                a,b = baseline[state],before[state]
                scenario_rows.append((text(lang,key),text(lang,'met' if state=='achieved' and i==0 else state),esc(a),esc(b),f'{b-a:+d}'))
        comparison = table([tr(lang,k) for k in ('goals','result','baseline','candidate','difference_short')],scenario_rows)
        tiles = figures([(changed,text(lang,'scen_changed')),(f'{overdue:+d}',text(lang,'scen_overdue')),(f'{risk:+d}',text(lang,'scen_risk'))])
        household = f'<p>{say(lang,"scen_household",n=inherited)}</p>' if inherited else ''
        scenario = (f'<section class="panel" id="scenario"><div class="section-head"><h2>{text(lang,"scenario2027")}</h2>{tip(lang,"help_scenario")}</div>'
                    f'<p>{text(lang,"scen_lead")}</p>{tiles}{household}<details><summary>{text(lang,"scenario_details")}</summary>{comparison}</details>'
                    f'<p class="legend">{text(lang,"scen_confirm")} · {esc(rules.RESPONSIBILITY_POLICY["version"])}</p></section>')

    reasons = {}
    for case in cases:
        for _,reason,_ in case['zemis_findings']:
            reasons[reason] = reasons.get(reason,0)+1
    people = sum(1 for c in cases if c['zemis_findings'])
    if people:
        zemis_body = figures([(people,text(lang,'zemis_people'))]+[(reasons.get(k,0),text(lang,k)) for k in ('zemis_no_overlap','zemis_employer_unknown','zemis_dates_unknown')])
        if can_queue:
            zemis_body += f'<a class="button" href="{href("/queue",state="zemis")}">{text(lang,"zemis_link")}</a>'
    else:
        zemis_body = f'<p>{text(lang,"zemis_none")}</p>'
    zemis = (f'<section class="panel" id="zemis"><div class="section-head"><h2>{text(lang,"zemis_title")}</h2>{tip(lang,"help_zemis")}</div>'
             f'<p>{text(lang,"zemis_lead")}</p>{zemis_body}</section>')

    values = report['values']
    top = max(values+[report['hi']])
    bars = ''.join(f'<meter min="0" max="{top}" value="{v}" aria-label="{i+1}: {v}">{v}</meter>'
                   for i,v in enumerate(values[-24:],len(values)-23))
    dates = [row[0] for row in series] if series else [rules.months(date(2022,1,1),i).strftime('%Y-%m') for i in range(len(values))]
    observations = table([tr(lang,'month'),tr(lang,'count')],((esc(month),esc(v)) for month,v in zip(dates,values)))
    forecast_month = rules.months(date.fromisoformat(dates[-1]+'-01'),report['horizon']).strftime('%m.%Y')
    checks = table([tr(lang,'forecast_model'),tr(lang,'gate_error'),tr(lang,'heldout_error')],
                   ((text(lang,'model_'+k),esc(report['gate_mae'][k]),esc(v)) for k,v in report['mae'].items()))
    status = f'{text(lang,"model_"+report["model"])} · {text(lang,"heldout")} {report["heldout"]} · {text(lang,"interval_coverage")} {report["coverage"]:.0%}'
    series_meta = f'{esc(dates[0])} → {esc(dates[-1])} · {len(values)} · '+text(lang,'aggregate_local' if series else 'demo')
    controls = ''
    if can_upload:
        controls = '<p>'+text(lang,'aggregate_help')+'</p>'+post('/forecast-upload',csrf,
            '<label>CSV <input type="file" name="series" accept=".csv,text/csv" required></label>'+action(lang,'aggregate_upload')+tip(lang,'help_csv'),True)
        if series:
            controls += post('/forecast-reset',csrf,action(lang,'aggregate_reset')+tip(lang,'help_csv_reset'))
    arrivals = f'''<section class="panel" id="arrivals"><h2>{text(lang,'arrivals_title')}</h2><p>{text(lang,'arrivals_lead')}</p>
<div class="two"><div class="reading"><h3>{text(lang,'interval')} · {forecast_month}</h3><strong class="forecast-value">{report['est']} <small>{report['lo']}–{report['hi']}</small></strong>
<p>{status}</p><div class="series" aria-hidden="true">{bars}</div>{tip(lang,'help_data_card')}<details><summary>{text(lang,'data_card')}</summary>
<p>{series_meta}</p>{observations}</details></div>
<div><h3>MAE</h3><p>{text(lang,'validation_months')} · {report['validation_months']}<br>{text(lang,'gate_months')} · {report['gate_months']}</p>{checks}</div></div>
<h3>{text(lang,'public')}</h3><p>{text(lang,'public_note')}</p><a href="{FSO}">{text(lang,'source')} · BFS / FSO</a>{controls}</section>'''
    return heading(lang,'forecast',text(lang,'plan_lead'))+f'<div class="section-head">{jump}</div>'+payments+scenario+zemis+arrivals


def privacy(lang):
    cards = ''.join(f'<section class="panel pv-card">{icon(name,"kpi-icon")}<h2>{text(lang,key)}</h2><p>{text(lang,key+"_text")}</p></section>'
                    for name,key in (('homes','pv_stay'),('queue','pv_roles'),('privacy','pv_leave')))
    flow = ''.join(f'<li>{text(lang,f"pv_flow_{i}")}</li>' for i in range(1,6))
    access = {'pv_cases':('cell_all','cell_own','cell_no','cell_no'),'pv_overview':('cell_all','cell_own','cell_sums','cell_no'),
              'pv_export':('cell_all','cell_own','cell_sums','cell_no'),'pv_import':('cell_all','cell_no','cell_no','cell_all'),
              'pv_plan':('cell_all','cell_no','cell_sums','cell_no'),'pv_intake':('cell_all','cell_own','cell_no','cell_all')}
    rows = ((text(lang,area),*(f'<span class="access {cell}">{text(lang,cell)}</span>' for cell in cells)) for area,cells in access.items())
    who = table([tr(lang,'pv_area')]+[tr(lang,'role_'+r) for r in ('judge','worker','manager','importer')],rows)
    listing = lambda key,n:'<ul class="plain">'+''.join(f'<li>{text(lang,f"{key}_{i}")}</li>' for i in range(1,n+1))+'</ul>'
    return (heading(lang,'privacy',text(lang,'pv_lead'))+f'<div class="three">{cards}</div>'
            f'<section class="panel"><h2>{text(lang,"pv_flow")}</h2><ol class="flow">{flow}</ol></section>'
            f'<section class="panel"><h2>{text(lang,"pv_who")}</h2>{who}</section>'
            f'<div class="two"><section class="panel"><h2>{text(lang,"pv_stored")}</h2>{listing("pv_stored",4)}</section>'
            f'<section class="panel"><h2>{text(lang,"pv_out")}</h2>{listing("pv_out",3)}</section></div>'
            f'<section class="panel ai-panel"><div class="section-head"><h2>{text(lang,"pv_ai")}</h2><span class="ai-badge">{text(lang,"ai_badge")}</span></div>{listing("pv_ai",4)}</section>'
            f'<section class="panel"><h2>{text(lang,"pv_delete")}</h2><p>{text(lang,"pv_delete_text")}</p><p class="legend">{text(lang,"pv_demo")}</p></section>')


def guide(lang,role):
    menus = menus_for(role)
    order = [('reports','/reports'),('overview','/overview'),('queue',href('/queue',state='week')),('case',href('/queue',state='week')),
             ('forecast','/forecast'),('intake','/intake'),('ai','/ai')]
    steps = ''.join(f'<li><h3>{icon("queue" if key=="case" else key,"nav-icon")}{text(lang,key)}</h3><p>{text(lang,"step_"+key)}</p>'
                    f'<a href="{link}">{text(lang,"guide_open")} →</a></li>'
                    for key,link in order if (key if key!='case' else 'queue') in menus)
    terms = ''.join(f'<div><dt>{text(lang,"g_"+k)}</dt><dd>{text(lang,"g_"+k+"_text")}</dd></div>'
                    for k in ('a1','work','household','lights','target','cutoff','small','zemis'))
    return (heading(lang,'help',text(lang,'guide_lead'))+f'<section class="panel"><h2>{text(lang,"guide_steps")}</h2><ol class="steps">{steps}</ol></section>'
            f'<section class="panel"><h2>{text(lang,"glossary")}</h2><dl class="glossary">{terms}</dl></section>')


def login(lang,csrf,error=''):
    return '<section class="login-hero"><img class="bern-image" src="/static/bern.jpg" alt=""><div><div class="login-signature"><img class="brand-mark" src="/static/stadt-bern-shield.png" alt="Stadt Bern"><p class="eyebrow">'+text(lang,'demo')+'</p></div><h1>Integrations-<br>Cockpit Bern</h1><p>'+text(lang,'lead')+'</p></div></section><section class="login-card"><img class="login-logo" src="/static/stadt-bern-logo.png" alt="Stadt Bern">'+heading(lang,'login')+(
        f'<p class="feedback" role="alert">{text(lang,error)}</p>' if error else '')+post('/login',csrf,
        f'<label>{text(lang,"username")}<input name="username" autocomplete="username" required></label>'
        f'<label>{text(lang,"password")}<input name="password" type="password" autocomplete="current-password" required></label>'
        +action(lang,'login')+tip(lang,'help_login'))+'</section>'


def state_cell(lang,state):
    return Cell(f'{LIGHT_SYMBOLS[state]} {tr(lang,state)}','state_'+state)


def export(lang,snapshot,cases,role):
    keys = ('a1','work','household')
    source = tr(lang,'demo' if snapshot['source']=='synthetic' else 'local')
    import json
    asof = date.fromisoformat(snapshot['asof'])
    tabs = {tr(lang,'data_card'):[[tr(lang,'field'),tr(lang,'value')],[tr(lang,'snapshot'),asof],[tr(lang,'source'),source],[tr(lang,'policy'),rules.VERSION]]}
    tabs[tr(lang,'data_card')].append([tr(lang,'reference_end'),rules.RESPONSIBILITY_POLICY['version']])
    coverage = [[tr(lang,'source'),tr(lang,'rows')]]+[[key,n] for key,n in json.loads(snapshot['inspected']).items()]

    def details(index, selected):
        for case in selected:
            g = case['goals'][index]
            row = [case['home'] if index==2 else case['id'],case['worker'] if index!=2 else None,
                   case['entry'].year if case['entry'] and index!=2 else None,
                   g['deadline'],g['achieved'],tr(lang,g['reason']),
                   ', '.join(f'{DATASET_NAMES.get(dataset,dataset)} {line}' for dataset,line in g['evidence']),state_cell(lang,g['state'])]
            if index==0:
                due = {True:'due_now',False:'upcoming_due',None:'due_unknown'}[g.get('due')]
                dates = ', '.join(map(swiss,g.get('official_dates',())))
                row += [case['entry'],tr(lang,g['scope']),tr(lang,due) if g['scope']=='scope_in' else None,
                        dates or None,tr(lang,'undated_proof') if g.get('official_undated') else None,
                        tr(lang,'uncertain_proof') if g.get('proof_uncertain') else None]
            elif index==1:
                row += [', '.join(map(swiss,g.get('official_dates',()))) or None,
                        tr(lang,'undated_proof') if g.get('official_undated') else None,
                        case['reference_end'],case['transition_end'],g['earliest']]
            else:
                row[6] = ', '.join(f'{DATASET_NAMES.get(dataset,dataset)} {line}' for dataset,line in g['evidence'] if dataset!='official')
                row += [g.get('period_start'),g['earliest']]
            yield row
    for i,key in enumerate(keys):
        selected = {c['home']:c for c in cases if c['goals'][i]['state']!='na'}.values() if i==2 else cases
        summary = rules.counts(cases,i)
        tabs[tr(lang,key)] = [[tr(lang,key),tr(lang,'rows')]] + [
            [state_cell(lang,state),number] for state,number in sorted(summary.items())
            if role!='manager' or (snapshot['source']=='synthetic' and number>=rules.MIN_GROUP)]
        if role!='manager':
            headers = ['ID',*[tr(lang,k) for k in ('worker','year','deadline','attained','reason','evidence')],tr(lang,'result')]
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
                [key,*rules.a1_totals(items)] for key,items in sorted(groups.items())] + [
                [Cell(tr(lang,'total'),'bold'),*(Cell(n,'bold') for n in rules.a1_totals(cases))]]
        tabs[tr(lang,'control_totals')] = [[tr(lang,k) for k in rules.A1_TOTALS],rules.a1_totals(cases)]
        tabs['ZEMIS'] = [[tr(lang,'case_identifier'),'ZEMIS',tr(lang,'result'),tr(lang,'evidence')]] + [
            [case['id'],line,tr(lang,reason),','.join(map(str,workbook_rows))]
            for case in cases for line,reason,workbook_rows in case['zemis_findings']]
        planned = sorted(((c,rules.next_action(c,asof)) for c in cases),key=lambda item:(item[1]['rank'],str(item[1]['when'] or '9999'),item[0]['id']))
        tabs[tr(lang,'this_week')] = [[tr(lang,'case_identifier'),tr(lang,'worker'),tr(lang,'next_step'),tr(lang,'when'),
                                       *(tr(lang,k) for k in ('a1','work','household'))]] + [
            [c['id'],c['worker'],unescape(action_label(lang,a)),a['when'],*(state_cell(lang,g['state']) for g in c['goals'])]
            for c,a in planned if a['week']]
    tabs[tr(lang,'coverage')] = coverage
    return tabs
