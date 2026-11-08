# Function-list follow-up review

The supplied list contains 163 logical responsibilities across nine sections. The original text is preserved in FUNCTION_LIST.md; FUNCTION_COVERAGE.md maps every entry to grouped implementation locations and records limitations. Rebuild the mapping with `node scripts/audit-functions.cjs`. This review does not replace the earlier audit's provider verification limits.

## Changes

- Added a transaction-event outbox using existing audit records. Imports publish within their database transaction; the worker refreshes forecasts and marks pending events processed together. Per-user locking serializes retries and duplicate publication. Events are local to this application, without an external broker.
- Added admin-only operational metrics at `/api/v1/system/metrics`. Counters report HTTP route templates, status, cumulative request duration, and process uptime. They exclude raw URLs, query strings, and user identities. Metrics reset on process restart and do not aggregate multiple workers.
- Added optional background retention for generated summaries and their audio. `SUMMARY_RETENTION_DAYS=0` preserves existing behavior; positive values remove expired summaries by creation time. Financial source records and audit/consent history remain intact. Users can also delete their own summaries/audio using `DELETE /api/v1/finance/summaries/{id}`.
- Extended summary requests with an optional hypothetical shock (`scenario.amount`, `scenario.due_date`). Verified forecast comparisons and explicit contingency steps are available to Gemini, and scenario assumptions and contingency steps cannot be omitted from the final text. No actual shock, installment, or scheduled payment is created.
- Removed obsolete router comments about future engine mounting.

## Folder cleanup

Removed 26 empty directories: eight obsolete engine placeholders and their empty test directories, four unused integration placeholders, three unused shared placeholders, the unused workers placeholder, and infrastructure/docker plus its empty parent. All paths were checked to remain inside the workspace; only directories empty at deletion time were removed. No source or financial records were removed. A final source-tree scan found zero unused empty project directories.

Environment/package-manager directories (`.git`, `.venv`, `node_modules`, `.pytest_cache`, and `__pycache__`) were excluded because their structure is managed by their owning tools. Links/junctions were not traversed.

## Verification

Final backend run: **109 passed in 42.33 seconds** (`.venv/Scripts/python.exe -m pytest -q --tb=short`). Frontend: **9 passed, 0 failed**, including an isolated real FastAPI/SQLite process (`npm.cmd test`). JavaScript syntax checks passed for the dashboard and inventory script. The inventory script successfully mapped 163 functions. Tests used isolated databases, and provider responses were fixtures; no live credentialed provider calls or database encryption verification were performed. Python and the live frontend server required sandbox escalation to access the installed interpreter; both completed successfully with that access.

## Remaining acceptance limits

Financial records are not encrypted by application-level database column types. Password hashing and token signing do not satisfy financial-data encryption. Database/disk encryption, backup encryption, database TLS, service deployment controls, and the complete source/audit/consent retention schedule require operator configuration and verification. Automatic source-data deletion was not enabled without a defined policy.

Banking, underwriting, Gemini, ElevenLabs, browsing-context, and external push delivery retain their explicit configuration requirements. Contract tests establish local behavior and failure handling, not real provider acceptance. A suspicious transaction generates a review notification; a bank-side hold or identity challenge requires a banking integration. Credit offers remain local planning proposals, not disbursements. These limits are also called out against individual entries in FUNCTION_COVERAGE.md; the application is not certified as satisfying every function in production.
