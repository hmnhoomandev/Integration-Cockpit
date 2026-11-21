# Verification

## Synthetic monthly imports

The default dataset has 144 people and 72 households. The A1 due date for DEMO-00001 is 16 October 2026. In September it needs follow-up. In October, a fide certificate dated 12 October changes the computed status to on time. The formal achievement row is absent in this fixture and the discrepancy remains visible.

An independently installed openpyxl reopened the exported workbook, verified the case/date values, sheet row counts and autofilter ranges. Application tests exercise all 11 workbook contracts, transactional failed imports, idempotent sandbox replay, role gates, locale-specific pages and exports, Excel date epochs, leap years, work threshold and gaps, suppression and privacy-gateway denials.

## Forecast

Default synthetic series, seed 2026. Rolling one-month experiment with 12 held-out months. MAE in counts: last observation 1.75, seasonal naive 5.17, trend 3.36. The trend failed the earlier baseline gate, so the demo uses the last-observation baseline. These numbers are measurements of the synthetic series.

## Throughput

Measured on the local macOS laptop with CPython 3.14.6, using the synthetic 11-workbook import, full rule evaluation and Excel export. Peak RSS is the process high-water mark. Times are seconds.

| People | Source rows | Generate | Import | Evaluate | Export | Peak MiB |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 8,331 | 0.23 | 1.30 | 0.09 | 0.07 | 73.9 |
| 10,000 | 82,104 | 2.19 | 12.43 | 1.00 | 0.73 | 531.7 |
| 40,000 | 328,013 | 9.04 | 71.68 | 6.57 | 4.19 | 2,020.9 |

One million rows have not been verified. Long imports should use the CLI.

## Browser

Chrome exercised the HTTPS judge site at desktop and 390 px mobile widths. Verified anonymous redirects, successful login, DE/EN/FR switching, two synthetic snapshot replays, A1 before/after, Excel download, source citation, aggregate forecast, protected upload route and logout.

The local Chrome run additionally uploaded all 11 synthetic XLSX files via the form, extracted a filled synthetic PDF, confirmed its proposed category without rendering a narrative canary, and verified aggregate CSV replacement and reset. The final regression suite passed 19 tests. A browser-discovered CSRF race from background favicon requests was fixed and regression-tested.

## Production rehearsal

The deployment smoke command verified live HTTPS and anonymous route protection, German/French/English, both month replays, the October evidence in the downloaded Excel, the rules assistant, forecast, and logout. A GitHub Actions workflow now runs the regression suite on Python 3.12 and 3.14 on each push and pull request.
