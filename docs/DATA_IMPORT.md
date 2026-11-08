# Processed dataset import

The supplied files are preserved separately from user-owned accounts and transactions. No account currency is declared in the files; no CAD conversion or fabricated transaction/merchant data is inferred. Existing user accounts and dashboard records remain unchanged, as requested.

| Source | Database table | Key |
| --- | --- | --- |
| data/processed/accounts_master.parquet | source_dataset_accounts | dataset_id, account_id |
| data/processed/monthly_summary_compact.parquet | source_dataset_monthly | dataset_id, account_id, month |
| data/processed/macro_insights.json | source_dataset_insights | dataset_id |

Tables are in the core schema on PostgreSQL and the main database on SQLite. The dataset ID is `financial_resilience_processed_v1`. JSON payload columns retain every original source field and value, including the account metrics and monthly totals. Insights include a source_manifest with file sizes, SHA-256 hashes, source counts, date range, and the explicitly unspecified currency. The monthly composite foreign key prevents orphaned references when database FK enforcement is enabled. Primary keys prevent duplicate accounts and periods.

After signing in, the **Imported dataset** section at the top of the dashboard displays source counts, account profiles, regional summaries, paginated accounts, source-account ID search, full source snapshots, and monthly histories. These amounts use source units rather than CAD formatting. The personal overview continues to use only your own financial records. If an older dashboard is cached, restart the server and hard-refresh the page with Ctrl+F5.

Finding a source account by ID or choosing **View history** also switches the financial overview cards, balance outlook chart, projected pressure table, recommendations, and pyramid to a read-only analysis of that account. A context banner identifies the account and historical reporting date; **Show my personal finances** restores the original view, including after refresh. Plans, offers, notifications, AI summaries and other personal tools continue to use personal data. No source-selection action writes to those records.

Source-account analysis is returned in the account-detail API's `analysis` field. It uses the last recorded month-end balance (rather than the processed summary's B metric), up to twelve completed months of income/spending, and the existing regression/forecast engine. Projection dates start the day after that recorded month-end. The pyramid uses the last month's household bills, insurance, loan payments, and cash/card withdrawals; withdrawals map to Peak under the app's category convention. Fees and other transfers without a reliable category remain explicitly unclassified and suppress a complete pyramid health score. Missing category data is not inferred as groceries or other living costs. Source units are never presented as CAD, and historical projections are not presented as current-date forecasts.

Public read-only endpoints: `GET /api/v1/datasets/overview`, `GET /api/v1/datasets/accounts?offset=0&limit=25&account_id=20111` (the account filter is optional), and `GET /api/v1/datasets/accounts/{account_id}`. Pagination is capped at 100 records per request. Source ID lookup and transaction history no longer require sign-in. Personal `/finance` routes and administrator `/system/metrics` routes retain their authentication and authorization requirements. Public sign-up is disabled by default; the page has an optional administrator login.

## Additional CSV sources

The nine CSV files directly in `data/` are imported using `python -m scripts.import_csv_dataset`, after `python -m scripts.migrate`. All original CSV column values are retained as strings (including empty strings and numerical formatting) in `source_dataset_records.payload`. The key is dataset/source/source-record-key; account IDs and dates/months are indexed for account browsing. `source_dataset_files` records checksums, counts, columns, and import times. Account references are validated; identical files skip reimport after their stored count is checked. Duplicate keys, malformed records, missing accounts, or changed files cause the import transaction to roll back. Omitted historical keys are not automatically deleted.

Run `python -m scripts.verify_csv_dataset` to compare every stored payload and count with the CSV sources. Results are saved in CSV_IMPORT_REPORT.json. The dashboard shows imported source counts under **Imported CSV source files**, and selecting a source account displays its paginated transaction history. `GET /api/v1/datasets/accounts/{account_id}/transactions?offset=0&limit=50` exposes that history as read-only source data. No merchant names, currency conversions, personal consent, or banking-user associations are inferred from the CSVs.

The added files contain 1,265,006 source rows: 77 districts, 4,500 accounts, 5,369 clients, 5,369 dispositions, 892 cards, 682 loans, 6,471 standing orders, 185,326 monthly summaries, and 1,056,320 transactions. A second import returned `already_imported` for all nine sources. The actual-database API check confirmed nine source manifests and a populated 50-row transaction page. Regression checks passed: 113 backend tests and 11 frontend tests. A backup was taken before the CSV migration/import; existing personal records and the processed dataset still match the backup/source verification.

The CSV importer and verifier work from temporary local snapshots to avoid cloud-file access interruptions while streaming the larger files. An initial interrupted attempt rolled back; only the successful complete retry was committed.

Run from the project root:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[data]"
.\.venv\Scripts\python.exe -m scripts.import_dataset --dry-run
.\.venv\Scripts\python.exe -m scripts.migrate
.\.venv\Scripts\python.exe -m scripts.import_dataset
.\.venv\Scripts\python.exe -m scripts.verify_dataset
```

The importer validates source account uniqueness, monthly uniqueness, references, month formatting, finite JSON values, and the macro account count before writing. It commits the entire import in one transaction. Identical files and matching row counts return `already_imported`; primary-key upserts handle retries without duplicates. Revised files update matching source keys without deleting omitted historical records; the verifier requires an exact source match and will report any additional records, so use a separately reviewed migration for a replacement dataset with removed keys.

The importer uses the same configured database as the app. This import used the local SQLite fallback, `financial_resilience.db`; the localhost PostgreSQL instance was unavailable. A pre-import SQLite backup was created in backups/. See DATA_IMPORT_REPORT.json for the backup path, exact counts, source hashes, full payload verification, and comparison of pre-existing tables. Backups and database files are excluded by the repository's `*.db` ignore rule.

Example queries (SQLite):

```sql
SELECT COUNT(*) FROM source_dataset_accounts;
SELECT MIN(month), MAX(month), COUNT(*) FROM source_dataset_monthly;
SELECT account_id, json_extract(payload, '$.region') AS region,
       json_extract(payload, '$.B') AS source_buffer
FROM source_dataset_accounts LIMIT 10;
SELECT month, json_extract(payload, '$.money_in') AS income,
       json_extract(payload, '$.money_out') AS expenses
FROM source_dataset_monthly WHERE account_id = 20111 ORDER BY month;
```
