# Acceptance matrix

| ID / phase | Status | Evidence and remaining dependency |
| --- | --- | --- |
| SHELL / 1 | Verified prototype | Python CLI and SQLite, versioned exact German headers for all 11 workbooks, report date and date of import stored separately. |
| IMPORT / 2 | Verified prototype | Synthetic two-month ingestion, hashes, row diagnostics, identifiers and transaction rollback. Observed German headers can occur in a different order. Unverified municipal workbook variations are rejected safely. |
| ASD-1 / 3 | Verified prototype | A1 deadlines, proof types, separate official evidence, follow-up, reconciled localized Excel. ASD still needs to confirm qualifying language and proof precedence. |
| ASD-3 / 4 | Partial | Goal 2 model validates calendar continuity and education. Real primary market eligibility requires evidence beyond the observed template categories. Goal 3 only treats generated coverage as complete. Household cutoffs and changing membership require institutional approval. |
| ASD-2, INTAKE / 5 | Partial | Cohort counts, fixed synthetic factors, suppression, reviewed local PDF proposal. Confirmed local categories can be compared in synthetic snapshots with suppression. Image-only PDF OCR passed in Linux CI. Representative institutional scan quality and additional factor strata remain open. |
| ASD-4 / 6 | Verified core journeys | Queue, evidence, timelines, snapshot selection and XLSX work in three languages. Raw source terms and some technical messages remain German or English by design or limitation. |
| PAY, RULE27, ZEMIS, LOAD / 7 | Partial | Illustrative A1 tariff, candidate 2027 cutoff count, overlap-based ZEMIS alerts and assignment caseload. Amounts and actual cohort logic require ASD validation. |
| ACCESS, AI-GW, AI-RULE, AI-GROUP / 8 | Verified fallback and access | Signed-out denial, roles, CSRF, session expiry, allowlisted inputs and cited topic retrieval. Four rules topics use local cited retrieval. No LLM adapter was used. Authorization and approval of model hosting, if added, remain open. |
| SCALE / 9 | Partial | Run timings and actual workload in [verification](VERIFICATION.md). Architecture materializes snapshot rows for calculations. One million source rows, concurrency under institutional load, and production failover remain unverified. |
| HANDOFF / 10 | Verified demo profile | Public temporary HTTPS with authenticated synthetic demo, repo documentation, Excel and video assets. Durable hosting, municipal SSO and institutional governance remain open. |

## Forecast

An independent 48-month generated workload series demonstrates the validation pipeline. Time windows are model selection, six-month baseline gate and a final twelve-month test. Interval width comes from selection-window residuals. Uploaded local aggregates may replace the series; source labels identify the origin. Comparable approved ASD longitudinal data and externally validated intervals remain open.
