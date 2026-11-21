# Integrations-Cockpit Bern

[Deutsch](docs/README.de.md) · [Français](docs/README.fr.md) · [Three-minute pitch](docs/PITCH.md) · [Submission copy](docs/SUBMISSION.md)

A prototype for the City of Bern’s asylum social service at the AI for Access hackathon. It turns the same 11 monthly Excel exports into explainable deadline checks for caseworkers and an aggregate reporting view for managers.

## Demonstration

[Version 1.0.0 acceptance and remaining deployment dependencies](docs/PHASE-10.md).

[Temporary HTTPS sign-in](https://listening-brian-served-upcoming.trycloudflare.com/login). It serves an isolated synthetic-only profile and depends on the demo laptop and tunnel staying online. The team distributes the username and password privately. [Narrated demo and sample artifacts](https://github.com/hmnhoomandev/Integration-Cockpit/releases/tag/v1.0.0).

1. Sign in and try the German, English and French interface.
2. In **Data & reports**, re-import September 2026. Open case **DEMO-00001**. A1 is due on 16 October and needs follow-up.
3. Re-import October 2026. The record now has a fide proof dated 12 October. Open the case again, see the discrepancy with the official achievement table, and download Excel.
4. Explore the cohort view, caseload, rules citations, privacy preview, synthetic forecast and illustrative 2027 calculation.

## Run locally

Requires Python 3.12+ with SQLite and scrypt. The runtime has zero external Python dependencies. For local PDF extraction, install Poppler on Linux or use macOS PDFKit. No spreadsheet or PDF package is needed for other workflows.

```sh
python3 -m cockpit.server serve --demo
```

Open http://127.0.0.1:8000. On a fresh database the command prints a randomly generated local credential once. Set or rotate an account interactively with `python3 -m cockpit.server account <username> <judge|manager|importer|worker>`. A worker additionally needs `--assignment A`, `B` or `C` for the seeded demo. Use a different database with `--db path` before the command. Use `delete-synthetic <snapshot-id>` for explicit synthetic-snapshot deletion.

```sh
python3 -m cockpit.server fixtures
python3 -m cockpit.server import 2026-10-31 runtime/fixtures/2026-10-31/*.xlsx
python3 -m unittest discover -s tests -v
python3 -m cockpit.benchmark 125000
python3 -m cockpit.reliability --workers 8 --rounds 3 --people 1000
```

## What the prototype covers

| Official challenge | Available behavior |
| --- | --- |
| 1. Language A1 | Current-scope screening, three-year deadline, eligible proof, separately cited official record, monthly reconciliation and Excel by caseworker and entry year |
| 2. Group analysis | Fixed entry cohorts and synthetic age, years of education and course observations, sample-size checks and Wilson intervals for completed follow-up |
| 3. Work, education and financial independence | Dated employment and education paths, distinct-household assistance intervals with conservative coverage handling |
| 4. Cockpit | Worker-scoped queue, case evidence and timelines, aggregate management UI, import and quality workspace |
| Extensions | 2027 cutoff comparison, illustrative CHF sensitivity, date-overlap ZEMIS discrepancies and caseload by assignment |

The **Rules assistant** uses approved, localized excerpts indexed by fixed topic and cites the original challenge by page. The **aggregate assistant** answers approved cohort and monthly-change questions using suppressed aggregate measures. **Intake review** extracts and links a report locally by ZEMIS and asks a human to confirm classifications. These workflows use retrieval and deterministic logic. No language model or hosted inference ran during verification.

The **forecast** uses a separate, reproducible 48-month synthetic planning series. It evaluates naive, seasonal-naive and trend models in time order, applies a baseline fallback gate, and measures MAE and interval coverage on 12 untouched months. Local judge and manager accounts can replace the series with a consecutive aggregate CSV and remove it to restore the synthetic series. The public FSO benchmark is displayed separately with its different denominator. Forecasts are aggregate and illustrative.

## Architecture and deployment

```text
11 .xlsx → bounded OOXML parser → staged SQLite snapshot → rule engine → UI / Excel
Objective date + identity links             → scoped cases / fixed cohorts
Reviewed public rules                      → typed gateway → cited local retrieval
Authorized local PDF                       → local extraction → human confirmation
Aggregate month/count series               → rolling backtest → default or baseline estimate
```

The current prototype uses SQLite and Python’s standard-library HTTP server; the [container recipe](Dockerfile) runs the synthetic-only profile. Store the hosted database outside the image, provision an account out of band with the CLI, and terminate TLS at the approved reverse proxy. Keep hosted startup and credentials separate from local datasets. [Deployment details](docs/DEPLOYMENT.md) · [Production acceptance and recovery](docs/PRODUCTION.md) · [Security](SECURITY.md)

## Verification and remaining work

See the [acceptance matrix](docs/ACCEPTANCE.md), [source and rule register](docs/SOURCES.md), [verification notes](docs/VERIFICATION.md) and [exact worksheet headers](cockpit/schema.json). The challenge templates and municipal form are schema evidence and are excluded from the public repository. The synthetic generator, local workbook download and benchmark commands reproduce the demo artifacts. [Bern photo credit](docs/ASSETS.md)
