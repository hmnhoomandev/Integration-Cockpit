# Source and rule register

Edition 2026-11-21. The original municipal challenge PDFs are supplied privately. Their English and German versions both include the data model. The eleven workbooks and empty intake PDF were examined as source contracts. No template example is counted as a case or observation.

| Owner / source | Scope and permitted demo use |
| --- | --- |
| City of Bern ASD, Integrations-Cockpit challenge, pp. 1–2 and model appendices | Goal interpretation and required user workflows. Summarized in the rules assistant. |
| [Stadt Bern ASD](https://www.bern.ch/politik-und-verwaltung/stadtverwaltung/bss/sozialamt/asylsozialdienst) | Official service description and context. No individual data. |
| [SEM IAS](https://www.sem.admin.ch/de/integrationsagenda) and [SEM monitoring](https://www.sem.admin.ch/de/monitoring-integrationsfoerderung) | National program and monitoring definitions, separate from Bern operational interpretation. Citation context. |
| [FSO, 20 November 2026](https://www.bfs.admin.ch/en/newnsb/YskdJK6LxRTM) | Switzerland, 2025, population aged 15+. “More than four in ten” had a migration background. Displayed as a public observation. The cited release does not contain a comparable ASD workload series. |
| [FSO methodology](https://www.bfs.admin.ch/bfsstatic/dam/assets/349727/master) | 2014 integration indicator definitions, populations and denominators. Methodology citation only. |
| [Bern KDSG](https://www.belex.sites.be.ch/app/de/texts_of_law/152.04), [DSV](https://www.belex.sites.be.ch/app/de/texts_of_law/152.040.1), [cantonal FAQ](https://www.dsb.be.ch/de/start/fuer-behoerden/faq_zum_kdsg.html), [Bern FADS](https://www.bern.ch/themen/stadt-recht-und-politik/datenschutz/) | Authority references for a municipal deployment. The canton confirms revised KDSG applicability from 1 September 2026. |
| [Bern SAFG](https://www.belex.sites.be.ch/app/de/texts_of_law/861.1), [Swiss Federal DSG](https://www.fedlex.admin.ch/eli/cc/2022/491/en) | Confirm jurisdiction and current consolidated text with the designated authority before institutional use. |
| [AI for Access](https://hackathon.powercoders.org/en/) | Powercoders × Tech & Beyond, Bern 20–21 November 2026, public event and judging materials. |

## Operational decisions requiring ASD confirmation

| Rule | Demo behavior | Confirm |
| --- | --- | --- |
| G1, G2 scope | Explicit VA, F-FL, B-FL, B-RSFL, B-SL, age at report date, responsibility in effect | Suffix status treatment, age reference, late-in-window birthdays and active scope |
| G1 | A1+ German; telc/fide indicated in the source; separately display official achievement evidence; three calendar years from entry | Accepted language, proof evidence, missing dates, validated official-versus-computed precedence |
| G2 | ≥60% per Erwerb row; adjacent/overlapping qualifying intervals unioned; enrolment in Sek II or tertiary. The Erwerb template only offers `unselbstständig` / `selbstständig`, so both count as first labour market unless employer or remark names an employment or integration programme (`2. Arbeitsmarkt`, `Beschäftigungsprogramm`, …), which is excluded. A missing Erwerbsstatus goes to review | How the export marks second-labour-market jobs, adjacency, whether education starts or completes the goal, date inclusivity |
| Identifiers | Whole-number Klientennummer / ZEMIS cells (as in the templates) are read as text, e.g. `12345`. Fractional or out-of-range numbers are rejected | Whether exports can contain leading zeros that Excel would drop |
| G3 | Once per Dossier-Nr.; responsibility cutoff if members agree; coverage treated as complete for generated fixtures only | Coverage declarations, qualifying support types, transferred or changing household membership |
| 2027 | VA/F-FL illustration uses five calendar years from entry; source dates unaffected. A VA/F-FL member without a dated entry follows the household's shifted cutoff when all members share the same exported end | Real transition cohort, operational dates and tariffs |
| Risk colors | Deadline runway of 90 days, with explicit evidence review and late results | Triage policy and appropriate operational stages |

## Source mapping

Klient anchors clients by Klientennummer and ZEMIS. Events determine entry. Asylverfahrensstand supplies history and status crosschecks. Sprachstand supplies proof. Integrationszielerreichung preserves formal evidence. Erwerb and Integrationsförderung und Ausbildung support goal 2. Dossierperson links dated household membership. Finanzielle Unterstützung supplies household coverage events. Unterbringung supplies context. ZEMIS Tätigkeit supports employment reconciliation. The intake PDF can link only through an explicit verified header ZEMIS.

## Synthetic demo caseload

`python3 -m cockpit.server fixtures` writes the two demo months (30.09. and 31.10.2026): about 1,400 fictional people in about 510 households, six fictional caseworkers, generated from seed 2026 with the value lists of the eleven templates. Both months share one history, so October adds new arrivals, asylum decisions and new evidence. Identifiers (`DEMO-…`, `SYN-Z…`, `SYN-H…`) are invented. The generator plants these relationships so the group analysis has something to find. They are not estimates of real outcomes:

- A1 more likely with a language course in the first six months after entry
- A1 more likely with more years of schooling and Latin-script literacy
- A1 less likely with higher age at entry
- A1 less likely for parents of small children; the demo months carry fictional, already confirmed Situationsanalyse categories (childcare scheduling, schooling, course, housing) for three of four adults
- Employment more likely after an early course and with more schooling
- A household leaves social assistance after a job of 70 %+ lasting 8+ months; one in four returns

The course factor in the group analysis compares the time from entry to the first language course (within six months, later, none). Age bands are 16–24, 25–34 and 35+ at the report date.

