# Security and governance

The hosted profile is an authenticated, synthetic-only hackathon demonstration. The local prototype may be tested with authorized synthetic or anonymized fixtures. Municipal operation requires a separate deployment and assessment.

| Role | Individual records | Reports and import |
| --- | --- | --- |
| Worker | Assigned people, scoped server-side | Scoped Excel, local intake review |
| Manager | Aggregate screens | Aggregate synthetic Excel, private aggregate series upload in local profile |
| Import operator | No case browsing | Snapshot upload and reconciliation, local intake classification |
| Judge | Synthetic case access in hosted profile | Fixed synthetic snapshot replay, Excel and synthetic forecast |

Passwords use per-account scrypt salts. Session tokens are stored as SHA-256 digests with an eight-hour expiry. Cookies are HttpOnly and SameSite=Strict, and hosted cookies require HTTPS. Forms enforce CSRF tokens. Sign-in is throttled in process. Hosted profile disables arbitrary workbook, forecast-series and PDF uploads. Log records use event type, outcome and timestamp without cell contents or identifiers. Application HTML escapes evidence and limits active content with CSP. Workbook formulas and active embedded archives are rejected. XLSX export writes user strings as literal cells.

For intake, local PDF text is processed transiently and found identifiers are matched only within scope. SQLite holds approved categories, workbook rows, accounts, and audit events. The temporary file lives in a private operating-system directory. The app sends zero inference requests. Restrict files and backups to the operator, and use separate synthetic and institutional storage.

| Approval owner | Required before real operation |
| --- | --- |
| ASD data and casework owners | Confirm purpose, field minimization, data dictionary, reporting scope and rule decisions. Define intake review, corrections, deletion and evidence retention. |
| City IT | Require institutional identity and MFA, role provisioning, TLS, encrypted disks and backups, restore drills, event monitoring, patching and incident response. |
| City Bern FADS and responsible canton/Confederation authorities | Determine legal roles, disclosure conditions, processor arrangements and whether a data protection impact assessment is required. Review the revised Bern KDSG and DSV, SAFG and applicable federal obligations. |
| Approved inference owner | Approve any separate model infrastructure and controlled de-identification validation before allowing an adapter. |

Potential incidents should be escalated to the designated ASD/IT incident owner. Restrict access, preserve minimal incident evidence, assess scope and legal reporting obligations with the competent privacy function, and document containment and remediation. Manage access, correction and deletion requests through the municipal process. See the [official sources](docs/SOURCES.md).
