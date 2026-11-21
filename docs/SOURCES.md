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
| G2 | ≥60% in each verified primary-market row; adjacent/overlapping qualifying intervals unioned; enrolment in Sek II or tertiary | Exact employment categories, adjacency, whether education starts or completes the goal, date inclusivity |
| G3 | Once per Dossier-Nr.; responsibility cutoff if members agree; coverage treated as complete for generated fixtures only | Coverage declarations, qualifying support types, transferred or changing household membership |
| 2027 | VA/F-FL illustration uses five calendar years from entry; source dates unaffected | Real transition cohort, operational dates and tariffs |
| Risk colors | Deadline runway of 90 days, with explicit evidence review and late results | Triage policy and appropriate operational stages |

## Source mapping

Klient anchors clients by Klientennummer and ZEMIS. Events determine entry. Asylverfahrensstand supplies history and status crosschecks. Sprachstand supplies proof. Integrationszielerreichung preserves formal evidence. Erwerb and Integrationsförderung und Ausbildung support goal 2. Dossierperson links dated household membership. Finanzielle Unterstützung supplies household coverage events. Unterbringung supplies context. ZEMIS Tätigkeit supports employment reconciliation. The intake PDF can link only through an explicit verified header ZEMIS.
