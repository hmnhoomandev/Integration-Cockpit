# Integrations-Cockpit Bern

[Deutsch](docs/README.de.md) · [Français](docs/README.fr.md) · [Three-minute pitch](docs/PITCH.md) · [Submission copy](docs/SUBMISSION.md)

A prototype for the City of Bern’s asylum social service (ASD), built for the AI for Access hackathon. ASD already exports its case data as eleven Excel files every month. The cockpit reads those files and answers three questions:

- **Caseworker:** who should I contact this week, and why?
- **Management:** how many people reach each integration goal on time, per caseworker and per entry year, and what do those who succeed have in common?
- **Planning:** which reached goals can be claimed, what changes with the 2027 rule, and where do ZEMIS and our records disagree?

Everything runs on one machine. The data stay in a local SQLite file, and the browser is not allowed to load anything from outside the cockpit.

## Try it in two minutes

Requires Python 3.12 or newer. There are no Python packages to install.

```sh
python3 -m cockpit.server serve --demo
```

Open <http://127.0.0.1:8000>. On a fresh database, the command prints a one-time username and password. The demo loads two invented months, 30.09.2026 and 31.10.2026, with about 1,400 people in 520 households and six caseworkers.

1. **Fallführung → Diese Woche.** About 170 contacts, ranked by impact: first, deadlines that can still be met; then reached goals that lack the official record needed for payment.
2. **Open DEMO-00001.** In September, A1 is due on 16.10.2026. In **Daten & Berichte**, load October: a fide certificate dated 12.10.2026 has arrived. The goal is green, and the next step says the official record is still missing.
3. **Übersicht.** Shows target against actual for goal 1, by caseworker and by entry year. In the group analysis, choose *Sprachkurs*: people who start a course within six months reach A1 on time in 73 % of cases, those who start later in 28 %.
4. **Planung.** Shows payments and 103 reached goals that cannot be claimed yet. It also shows the 2027 rule, under which 544 people leave ASD’s responsibility earlier, and 27 ZEMIS mismatches.
5. **Demo-Rolle** (bottom of the sidebar). Switch to *Fallführung* to see only Anna Keller’s cases, or to *Leitung* to see totals only. The server enforces both.
6. **Download Excel.** Results come out as real dates in Swiss format, with coloured lights and a *Diese Woche* tab.

Every button has a yellow **!** next to it that explains what it does. **Hilfe** gives a short tour and a glossary, and **Datenschutz** explains where the data stay and who sees what.

## What it covers

| Challenge part | In the cockpit |
| --- | --- |
| Goal 1 · Language A1 | Who is in scope, three-year deadline from entry, accepted proofs, comparison with the official record, Level 1 target and actual by caseworker and entry year (on screen and in Excel) |
| Goal 2 · Work or education | Six uninterrupted months at 60 % or more in the primary labour market, or upper-secondary or tertiary education, before responsibility ends. Employment programmes do not count |
| Goal 3 · Financial independence | Twelve months in a row without social assistance for the whole household (Dossier-Nr.) |
| Level 2 · Group analysis | Entry year, age, schooling, mother tongue, course timing and confirmed intake categories. Rates come with 95 % ranges, and groups under eight people are hidden |
| Casework | Weekly list, traffic lights per goal, one next step per case, and the source rows behind every result |
| Extras | Payment estimate, 2027 rule comparison, ZEMIS check, arrivals forecast, local intake-PDF review, and a rules assistant with cited sources |
| AI | Group patterns on every open A1 case: how people in a similar situation did (groups of 8 or more, never a score per person, as the challenge asks), the features that make the biggest difference across the caseload, and the rate for the same group with an early language course. The patterns come from a logistic regression trained locally on completed cases (cross-validated AUC 0.78; nationality, mother tongue and gender excluded). A privacy shield masks names, birth dates, AHV, ZEMIS and client numbers, addresses, phone, email and IBAN before any text reaches a language model, and blocks the request if anything is still recognisable. Optional Claude analysis of aggregate figures and masked intake forms |
| Contact | Call and email links on every case, with templates in German, English and French. Demo contact details are invented; the eleven exports contain none |

The interface is in German, English and French. The demo data are invented. Some associations in the data were planted on purpose so the analysis has something to show; [docs/SOURCES.md](docs/SOURCES.md) lists them.

## Switching on the language model

The AI forecast and the privacy shield always run locally. The Claude analysis is off by default. To switch it on, only on a machine where the operator has approved it:

```sh
python3 -m pip install anthropic
export ANTHROPIC_API_KEY=…   # or use `ant auth login`
COCKPIT_AI=claude python3 -m cockpit.server serve --demo
```

Only masked text or aggregate figures are sent. Each request is logged as an event without content.

## Roles

| Role | Sees |
| --- | --- |
| Demo account | Everything, and can switch roles |
| Caseworker (`worker`) | Only their own cases |
| Management (`manager`) | Totals only; groups under eight people are hidden |
| Import (`importer`) | Import, quality report and intake review |

```sh
python3 -m cockpit.server account <username> <judge|worker|manager|importer> [--assignment "Anna Keller"]
```

## Public demo on Vercel

The repository deploys to Vercel as-is: `app.py` serves the hosted, synthetic-only profile, and three environment variables set the jury account and the session secret. See [docs/DEPLOY-VERCEL.md](docs/DEPLOY-VERCEL.md).

## Real data

```sh
python3 -m cockpit.server import 2026-10-31 path/to/*.xlsx
```

The import needs all eleven exports for one report date and checks their headers against [cockpit/schema.json](cockpit/schema.json). If a delivery is incomplete or faulty, it is rejected and the last valid version stays in use. A quality workbook names each problem by file, row and reason. The A1 rule and the responsibility periods live in [cockpit/a1-policy.json](cockpit/a1-policy.json) and [cockpit/responsibility-policy.json](cockpit/responsibility-policy.json), so ASD can adjust them without changing code.

## Checks

```sh
python3 -m unittest discover -s tests -v
python3 -m cockpit.benchmark 125000
python3 -m cockpit.reliability --workers 8 --rounds 3 --people 1000
```

The suite has 46 tests. The OCR test is skipped where Tesseract is missing.

## Architecture

```text
11 × .xlsx → bounded OOXML reader → SQLite snapshot per report date → rule engine → HTML / Excel
```

The cockpit uses only the Python standard library: http.server, sqlite3 and hashlib.scrypt. It sends a strict Content-Security-Policy, so no scripts and no external content run in the browser. [Deployment](docs/DEPLOYMENT.md) · [Production notes](docs/PRODUCTION.md) · [Security](SECURITY.md) · [Sources and rules](docs/SOURCES.md) · [Image credits](docs/ASSETS.md)
