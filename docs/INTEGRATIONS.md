# Integration contracts and configuration

No secrets are included in source. Set environment variables or a local, ignored `.env` file. Missing credentials produce explicit errors or a documented unavailable state. Tests use clearly identified fixtures, never fabricated production success.

## Public CPI

`STATSCAN_API_BASE_URL=https://www150.statcan.gc.ca/t1/wds/rest`, `STATSCAN_CPI_VECTOR=41690973` select Statistics Canada's national all-items monthly CPI. The app calls `POST /getBulkVectorDataByRange` with a single object containing `vectorIds`, `startDataPointReleaseDate`, and `endDataPointReleaseDate`, and persists returned reference-month observations. A live read-only check returned 49 observations through 2026-09 on 2026-11-07. No personal data is sent. Quarterly average CPI is rebased to the same latest monthly reference for every quarter. Missing quarter CPI is reported, never interpolated.

Official contract: https://www.statcan.gc.ca/en/developers/wds/user-guide

## Gemini

Set `GEMINI_API_KEY`, `GEMINI_MODEL_NAME` to a model available in your account, `GEMINI_REQUEST_TIMEOUT_SECONDS`, and `GEMINI_MAX_RETRIES`. The REST integration requests JSON Schema output via `responseJsonSchema`. There is no mock-success fallback. Explicit AI consent is required. Only verified metric statements and approved recommendations are supplied. The model selects their keys and approved empathetic phrases; the server validates every reference and renders all financial figures itself. This deliberately limits free-form conversation and eliminates unverified financial claims. Questions are supported as selection context, not as permission to invent projections or eligibility.

Official contract: https://ai.google.dev/api/generate-content

## ElevenLabs

Set `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` (professional), `ELEVENLABS_EMPATHETIC_VOICE_ID`, and optionally `ELEVENLABS_MODEL_ID` (default `eleven_multilingual_v2`). `POST /v1/text-to-speech/{voice_id}?output_format=mp3_44100_128` receives an already verified summary. Audio is stored in the same protected database and delivered through an owner-authorized endpoint with `Cache-Control: no-store`. The frontend fetches it with the bearer token and uses a temporary blob URL for native play/pause/replay. Voice generation is not automatically retried because it may incur duplicate usage charges. AI consent covers both named AI/voice services, as disclosed in the UI.

Official contract: https://elevenlabs.io/docs/api-reference/text-to-speech/convert

## Provider adapters requiring your infrastructure

No banking, underwriting, browsing, or notification vendor or credentials were supplied. These adapters implement the following **application-owned contracts**, not a claim of compatibility with an unnamed bank/vendor. Deploy a trusted adapter implementing them, or map your selected provider's schema here. All calls use HTTPS in production, bearer authentication, bounded timeout/retry, and server-controlled base URLs. Browser clients cannot choose provider URLs or eligibility outcomes.

| Service | Variables | Request and response |
| --- | --- | --- |
| Core Banking | `BANKING_API_URL`, `BANKING_API_KEY` | `POST /snapshot` with `{user_id,currency:"CAD"}`. Response `{accounts:[{local_account_id,snapshot:{institution_name,account_type,masked_account_number,current_balance,available_balance,currency}}],transactions:[TransactionInput]}`. Accounts must already belong to the user. Signed transaction amounts are positive income, negative expense. `external_id` is mandatory and idempotent per user. Sync atomically updates balance snapshots and imports history. History does not reapply to current balances. |
| Underwriting | `UNDERWRITING_API_URL`, `UNDERWRITING_API_KEY` | `POST /eligibility` with `{user_id,amount,currency}`. Response `{eligible:boolean,product:"credit"/"overdraft"/"none",reference:string,approved_amount:decimal}`. A positive decision must cover the requested shortfall. Unknown eligibility produces no installment offer. Eligible users receive the verified conventional route/reference in the UI. No credit is opened or disbursed. |
| Browsing Context | `BROWSING_API_URL`, `BROWSING_API_KEY` | `POST /context` with `{user_id,category,at,lookback_hours:72}`. Response `{matches:[{category,viewed_at:ISO_datetime_with_timezone}]}`. Only consented users are queried. Only matching categories within the preceding 72 hours reduce risk. Failure leaves the reduction unapplied and adds an explicit warning. |
| Notification | `NOTIFICATION_API_URL`, `NOTIFICATION_API_KEY` | `POST /deliver` with `{user_id,title,message}` and `Idempotency-Key`. Response `{delivered:true}` acknowledges delivery. The service must honor idempotency and map user identity to previously verified push destinations. Failed notifications remain persisted for retry. In-app alerts and browser notifications while the dashboard is open work without this adapter. |

`INTEGRATION_TIMEOUT_SECONDS=20` and `INTEGRATION_RETRIES=2` bound generic requests. Transport errors, 429 and 5xx can retry. 4xx authentication/validation errors do not retry. Provider errors never return a fabricated successful response.

## Lending terms and actual activation

Set both `INSTALLMENT_ANNUAL_RATE` (annual nominal percentage, e.g. 12) and `INSTALLMENT_FEE` (CAD, financed with principal) from approved business terms before alternative plans are generated. No interest rate or fee is assumed if either is missing. A plan is generated only following a real negative conventional eligibility response. It uses amortizing monthly interest and cent-rounded payments, with a reconciled final payment. Accepting requires explicit confirmation, an unexpired offer and a current term-wide affordability check. It atomically records local schedules and audit history, superseding sibling offers. **This is a local planning acceptance, not a lender contract or disbursement.** Real origination, underwriting product selection URLs, regulatory documents, repayment collection and bank posting need a selected lender and its API/business contract. Planned funding is labeled as an assumption and never alters actual liquidity snapshots.

## Worker and deployment

Forecast/subscription updates occur in the same transaction as financial events. No asynchronous broker is required to avoid losing updates. Periodic refresh, due-date catch-up reminders, and notification delivery run hourly by default. The API starts a worker unless `ENABLE_BACKGROUND_JOBS=false`. For multiple API processes, disable embedded workers and run exactly one `python -m app.engines.jobs` process. `JOB_INTERVAL_SECONDS` controls cadence. PostgreSQL user row locks serialize user mutations; uniqueness constraints provide durable event/notification/offer keys. Notification adapters must honor idempotency for crash recovery. SQLite is for local development, not multiworker financial workloads. Redis/RabbitMQ in the original Compose file remain optional, unused infrastructure; no Celery implementation is claimed.

The architecture remains a modular monolith. Calculations are independent of storage; services, schemas, API boundaries, and provider adapters are separated. Independent microservice deployment, distributed transport, and scaling verification are not claimed.

Final local verification: 105 backend tests and 9 frontend tests passed. Banking sync ownership/idempotency, provider retry/failure contracts, notification retry/deduplication, and private audio workflows are tested with explicit fixtures. These tests do not substitute for live credentialed provider acceptance tests.
