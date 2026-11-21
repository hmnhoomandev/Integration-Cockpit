# Production acceptance

| Phase | Acceptance evidence | Open dependency |
| --- | --- | --- |
| Ingestion and recovery | Streaming worksheets, reordered German column contracts, transactional validation, consistent private SQLite backup and restore regression | Approved representative ASD exports, written retention and backup policy |
| Rule decisions | Synthetic evidence for three objectives and 2027 scenario | Confirm language, evidence precedence, primary-labour-market evidence, assistance coverage, household changes, cutoff dates and actual rates |
| Intake and analytics | Local text extraction, optional three-page OCR with human verification, suppressed categories on synthetic snapshots | Verify quality on an approved representative scan corpus and approve any operational category collection |
| AI and forecasting | Allowlisted local retrieval, fixed aggregate questions and time-ordered forecasting | Approve an inference environment if generative AI is required. Supply comparable longitudinal aggregates before operational forecasts |
| Deployment | Authenticated synthetic delivery, tested release bundle and CI | Provide institutional hosting, SSO, disclosure authorization, backup encryption, access review, and a named operator |

## Recovery rehearsal

Create an online SQLite snapshot to a new path on a private, encrypted volume. The operation verifies SQLite integrity and refuses to replace any existing file.

```sh
python3 -m cockpit.server --db /private/cockpit.sqlite backup /private-backups/cockpit-copy.sqlite
```

Validate the copied database in an isolated loopback environment using `--db`. Backups include the source database's accounts, snapshots and sessions. Treat them as sensitive and preserve their restrictive file permissions. Before making a restored instance available, rotate affected credentials and invalidate sessions. Document and rehearse the institutional restoration and deletion process.

## OCR

Install Poppler and Tesseract with English, German and French language packs where appropriate. Intake attempts ordinary PDF text extraction first. Sparse documents without a header match can run bounded OCR on the first three pages. It requires a single exact known ZEMIS match and a human approval. Extracted narrative and page images are temporary. Blank, ambiguous or unreadable reports stay in manual review. The public synthetic profile restricts intake to its sample view.
