# Financial Resilience Engine

FastAPI application with a same-origin HTML/JavaScript dashboard, SQLAlchemy persistence, deterministic financial calculations, JWT authentication, and optional external integrations. The existing modular monolith is preserved; this is not eight independently deployed microservices.

## Run locally on Windows

Use Python 3.12 or newer. From this folder in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe -m scripts.migrate
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If the environment already exists, reuse it. If `py` is not installed, use your installed Python executable for the first command. The checked-in `.venv` on this machine points to a Python 3.14 installation; virtual environments are machine-specific and should be recreated if that interpreter is unavailable.

Open **http://localhost:8000/** for the dashboard. Register, add your own current account snapshots, import transaction history, and add income/obligation schedules. No demo financial data is seeded. **http://localhost:8000/docs** exposes the API. Stop with Ctrl+C.

The example PostgreSQL URL falls back to local SQLite only if the local database is unreachable. Cloud URLs never silently fall back. To select SQLite explicitly, set `DATABASE_URL=sqlite+aiosqlite:///./financial_resilience.db`. `scripts.migrate` can adopt the original development database after checking its layout, preserving records; back up real financial databases before any deployment migration. Production uses migrations rather than automatic schema creation.

## Capabilities

- Current liquidity, historical spending regression, 30/60/90-day forecasts, scheduled commitments, projected depletion, hypothetical shock comparisons, and recommendations with estimated runway impact.
- Fraud scoring with cumulative recurring discounts, permission-gated browsing context, recent chargebacks, geographic expectations, budgets, amount Z-scores, cart sizes, and typical times. Alerts request review rather than declaring fraud.
- Vacation dates, destination area, trip budgets, associated transaction details, and geographic coordinate plots.
- Monthly/annual recurring charge detection, billing reminders, overlapping services, wellness thresholds, and cancellation status tracking.
- Quarterly CPI-adjusted income/expense trends, purchasing-power warnings, and a visual 50/30/20 expense pyramid.
- Shock assessments and cent-reconciled 3/6/12-month installment plans following verified conventional-credit ineligibility and configured business terms. Acceptance requires confirmation and a current affordability assessment.
- Verified Gemini summary selection and authenticated ElevenLabs MP3 playback, when configured and consented.
- Persistent in-app alerts, optional browser alerts while the dashboard is open, and an external notification delivery adapter.

**Accepted offers are local plans, not lender contracts or disbursements.** Conventional credit needs a real underwriting adapter. Merchant cancellations are tracked, not executed. External services never return invented success when unavailable.

## Data and calculation conventions

Account balances are current CAD snapshots. Historical imports do not change them. Update balances manually or through banking sync as money moves. Transactions use negative expenses and positive income; external references deduplicate imports per user. Amounts are Decimal values rounded to cents; no exchange-rate conversion is inferred.

Forecasts use up to twelve completed calendar months, including intervening zero months, and flag fewer than six months. Outstanding schedules due today are included. Calendar schedules replace historical spending in their category to avoid double counting; recurring scheduled income replaces historical income, while one-time income supplements it. Detected subscriptions participate in the same projections and affordability calculations. Cancelled services are removed from projected recurring spending. Review these assumptions when entering mixed categories or incomplete history.

Budgets are monthly category limits; the budget fraud adjustment considers spending already recorded that month. Geographic scoring requires consent and coordinates. Vacation Mode only changes the expected geographic area. Fraud policy defaults start at 0.50 and apply each recurring 0.90 multiplier before browsing, chargeback, geography and budget adjustments. Every policy weight and the review/Z-score thresholds can be configured. CPI comparisons require complete quarter CPI; incomplete transaction quarters are labeled and do not trigger wage/overspending growth alerts.

## Configuration and verification

See [.env.example](.env.example) and [integration contracts](docs/INTEGRATIONS.md) for credentials, provider schemas, approved lending terms, retry behavior, and worker deployment. Do not commit `.env` or database files.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd ci --ignore-scripts
npm.cmd test
.\.venv\Scripts\python.exe -m scripts.verify_public_cpi
```

The Node dependency is development-only: jsdom exercises frontend interactions. One UI test launches a real isolated FastAPI/SQLite instance. The public CPI smoke check requires network access and sends no personal data. Other provider tests use labeled test fixtures. Browser visual inspection and real credentialed provider success are reported separately from automated tests.

For production, set a unique `SECRET_KEY`, `ENVIRONMENT=production`, `DEBUG=false`, `USE_LOCAL_FALLBACK_DB=false`, explicit CORS origins, PostgreSQL and HTTPS adapter endpoints. Apply `python -m scripts.migrate` before starting. Use one background worker: disable embedded jobs in multiple API instances and run `python -m app.engines.jobs` separately. SQLite is for local development. Docker Compose remains available with `docker compose up --build`; copy `.env.example` first. Docker builds were not verified in this environment.

## Audit evidence

- [Original requirements](docs/REQUIREMENTS.md)
- [Initial audit](docs/INITIAL_AUDIT.md)
- [Final requirement checklist](docs/FINAL_CHECKLIST.md)
- [Implementation report](docs/IMPLEMENTATION_REPORT.md)
