# Phase 10 · 1.0.0 acceptance and handoff

This release is the final synthetic hackathon delivery for the ten approved phases. It includes the application source, a fresh-browser walkthrough, the narrated demo and captions, generated monthly inputs, example reconciled outputs, privacy and operating documentation, and measured reliability evidence.

| Phase | Accepted in the synthetic release | Institutional dependency or limit |
| --- | --- | --- |
| 1 · Sources and shell | All 11 supplied workbook headers match the source contract; source PDFs, model and form reviewed; startup and authentication verified | The supplied templates have no real observations |
| 2 · Excel ingestion | Two generated months, alternate header order, rejected import rollback, row provenance, checksums and quality download | Representative authorized case-bearing exports |
| 3 · A1 and reconciliation | Status, due date, computed and official evidence, three-language filtered XLSX, matched control totals | ASD approval of qualifying language, status and proof precedence |
| 4 · Work, education and household | Calendar employment continuity, education alternative, household membership reset, distinct-household report, unknown coverage stays reviewable | ASD-approved evidence, assistance classification and responsibility rules |
| 5 · Analysis and intake | Fixed descriptive cohorts, uncertainty, sparse and complementary suppression, safe aggregates, exact ZEMIS review and OCR CI | Representative scans, supported data for adjusted comparisons, and approval to use sensitive group attributes |
| 6 · Cockpit and roles | Three languages and three synthetic personas, keyboard navigation, responsive views, permission enforcement | Independent accessibility review and municipal role mapping |
| 7 · Scenario and forecast | Baseline/candidate cutoffs, hypothetical tariffs, ZEMIS evidence and caseload, rolling 48-month synthetic forecasting, and local aggregate CSV replacement | Confirmed 2027 cohort and tariffs, comparable ASD history and prospective forecasting validation |
| 8 · AI and privacy | Dated cited retrieval, safe aggregate questions, human-reviewed local PDF suggestions, canary rejection and scoped access | No language-model adapter was activated; approved inference infrastructure and evaluation required if generative AI is commissioned |
| 9 · Scale and recovery | 1,024,755-row single-user CLI benchmark; 8 simultaneous sessions and 120 requests; restored backup with revoked sessions and verified export | Municipal network capacity, simultaneous institutional load, managed failover, retention and recovery objectives |
| 10 · Release | Published repository, verified synthetic HTTPS, portable bundle, pitch and submission copy | Durable hosting, municipal SSO and approvals; no formal organizer submission was sent |

## Verify and run

```sh
python3 -m cockpit.server serve --demo
python3 -m unittest discover -s tests -q
python3 -m cockpit.reliability --workers 8 --rounds 3 --people 1000
python3 -m cockpit.benchmark 125000
```

The hosted judge profile serves generated records only. The temporary HTTPS tunnel depends on this device. The container recipe provides a separate deployment path and still requires authorized hosting and TLS. The application deliberately uses SQLite and the standard library for a reproducible runtime without Python package installation. Consider a managed PostgreSQL migration for multi-instance hosting and test transactional snapshot isolation, indexing, durable sessions, encrypted backups and recovery in the target environment.

Ask ASD for a data dictionary, representative authorized export and scan samples, the goal baseline and outcome dates, timestamps and allocation rules for any approved factor, decision owners for the 2027 transition and tariffs, and the authorized environment and retention process. Real operational use starts only after those acceptance gates are met.
