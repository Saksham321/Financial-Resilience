# Requirement completion — November 8, 2026

This implements the code gaps from SPEC_COMPLIANCE_REVIEW.md. The earlier review remains a historical before-state. **Local implementation is complete for the changes below; external production activation is still dependent on provider contracts, credentials, approved lending terms, and deployment verification.** No credentials, approvals, or lender contracts were invented.

## Completed changes

| Area | Implemented behavior | Evidence |
| --- | --- | --- |
| Shock contract | Authenticated `POST /api/v1/shocks/mediate`, actor-ID validation, idempotency header, specification-shaped installment proposals, optional banking snapshot sync when configured, only affordable 3/6/12-month proposals, explicit no-affordable-plan outcome | app/api/endpoints/specification.py; test_requirement_completion.py |
| Liquidity | CHECKING, SAVINGS and CASH snapshots; the compatibility route uses a configured banking adapter before mediation or explicitly identifies stored snapshots | schemas.py, service.py; existing banking ownership/dedup tests |
| Predictive API | `POST /api/v1/predictive-plan`, validated 6–12-month window, minimum six completed months for that contract, essential/discretionary totals and recommendation impact fields | specification.py, calculations.py |
| ML classification | Real TF-IDF character-feature/Multinomial Naive Bayes model trained from labelled per-user merchant history. At least six labelled examples across two categories, with at least two examples per category, and confidence >=0.65. Exact supplied labels, merchant history and transparent keyword rules remain preferred. Insufficient/conflicting evidence leaves the description unclassified | categorization.py; test_completion_rules.py tests generalization and abstention |
| Fraud baseline | Strict 90-day risk window ending at transaction time; category and UTC-hour frequency profiles; geographic history restricted to that window; amount/cart distribution statistics. Lifetime qualifying recurring transactions still retain their cumulative merchant discount | service.py ingest; rolling-window integration test |
| Risk scoring | Category novelty, unusual time after at least six baseline records, and cart anomaly contribute configurable increments. Existing 0.50 baseline, 10% recurrence, browsing/chargeback/geography/budget weights, clamp, review threshold, and large-amount Z-score review remain | calculations.py, config.py; completion rules and existing financial tests |
| Browsing matching | Normalized aliases and Jaro-Winkler similarity >=0.90, still requiring explicit permission and a 72-hour timestamp match | categorization.py, providers.py; fuzzy-provider test |
| Billing jobs | Durable reminder records scheduled at 00:00 UTC exactly three calendar days before predicted billing. Future reminders are hidden/not delivered before due; cancelled or superseded billing reminders are cancelled. Worker polls due records and uses existing delivery deduplication/retries | scheduled_notifications_v1 migration; service.py, jobs.py; future/cancellation tests |
| Subscription state | `GET /api/v1/subscriptions` returns the requested IDs, merchant name, uppercase cadence, next billing date, three-day reminder date, overlap flag and overlapping IDs. Existing dashboard fields remain compatible | specification.py, service.subscription_records |
| Inflation | Up to four trailing calendar quarters of available records, retaining a preceding quarter only for QoQ context; missing quarters disclosed without fabricated transactions. Existing complete-quarter safeguards remain | calculations.inflation; four-quarter test |
| Pyramid | Canonical underscore/space/hyphen aliases including household_bills, loan_payments and transit. Correct income-based 50/30/20 ratios, visual_status, user_pyramid_ratios, proposed_rearrangement and reallocation amount | calculations.py, categorization.py; category and target tests |
| Gemini | Prompt includes predictive/pyramid/mediation/scenario context. Optional conversational generated summary and paraphrased actions are validated against selected numeric evidence; unsupported numbers and approval/guarantee claims are rejected. Verified facts/actions still accompany generated prose | ai_validation.py; finance.py, reference_review.py; grounded-prose and handoff tests |
| Automatic voice | Successful summary generation automatically sends finalized text to ElevenLabs when requested and consented. Personal MP3 is stored privately; source-review MP3 is returned inline and rendered in an audio player. Professional/empathetic profile controls and audio opt-out are present. Text survives voice-provider failure with a clear unavailable status | finance.py, reference_review.py, app.js, reference.js; exact-text/profile and UI tests |
| Deployment boundaries | Eight independently selectable ASGI engine applications with isolated route surfaces and health checks; optional Compose overlay. Only subscription service owns the embedded worker. Integrated dashboard remains the default | app/services.py, docker-compose.engines.yml; service-route/worker tests |

No new production subscription examples, historical datasets, approved lending parameters, consent grants, or personal financial records were fabricated to satisfy the requirements. Test data is confined to isolated test databases. Existing ZIP reference values remain separate from the specification workflows because their median/buffer, spending-share pyramid, CPI snapshot, subscription examples, and proxy-fraud assumptions intentionally differ.

## Operation

The local database was backed up to `backups/before_requirement_completion_20261108_001229.db` before the additive reminder migration. Existing source tables and account/password records were preserved. On another installation, apply migrations before starting:

```powershell
.\.venv\Scripts\python.exe -m scripts.migrate
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Refresh the browser with Ctrl+F5. Summary forms now include an automatic-audio checkbox and voice choice. The source toolkit's external-processing checkbox must be enabled for Gemini/ElevenLabs; browser speech remains available separately.

Financial API amounts continue to serialize as decimal strings to preserve cents; numeric JSON request values are accepted. The specification's example `usr_...` identifier is not a UUID: the compatibility contract uses the authenticated UUID and rejects attempts to mediate for another user. Example repayment amounts are not hard-coded to match an arbitrary sample.

Run a separate engine process, for example:

```powershell
$env:SERVICE_NAME='shock'
.\.venv\Scripts\python.exe -m uvicorn app.services:create_service --factory --port 8011
```

Supported names: shock, predictive, fraud, subscriptions, inflation, pyramid, gemini, voice. The optional Compose overlay uses ports 8011–8018:

```powershell
docker compose -f docker-compose.yml -f docker-compose.engines.yml --profile engines up --build
```

These applications deliberately share the current database and authentication model. This supplies separate process/deployment boundaries without claiming independently owned databases or distributed-transaction isolation. Use PostgreSQL and one scheduler in production. The Compose file was parsed and worker ownership checked; Docker is not installed here, so a container build/runtime is not claimed. The integrated frontend continues to use the default app; production routing for split services is an operator deployment choice.

## Remaining external acceptance gates

`python -m scripts.check_integrations` reports missing setting names without exposing keys. Current missing configuration:

- BANKING_API_URL and BANKING_API_KEY, with the snapshot contract in INTEGRATIONS.md.
- UNDERWRITING_API_URL and UNDERWRITING_API_KEY, with an actual eligibility/product contract.
- BROWSING_API_URL and BROWSING_API_KEY, with consented context data.
- NOTIFICATION_API_URL and NOTIFICATION_API_KEY, with real push destinations and delivery confirmation.
- GEMINI_API_KEY and a model available to that account.
- ELEVENLABS_API_KEY and authorized voice access; ELEVENLABS_EMPATHETIC_VOICE_ID is also unset.
- Business-approved INSTALLMENT_ANNUAL_RATE and INSTALLMENT_FEE for personal plans. Reference demo terms are not automatically treated as approved product terms.

The adapter/client code and local failure/success contracts are implemented. Without these inputs, real banking sync, underwriting, browsing retrieval, push delivery, Gemini generation, and ElevenLabs synthesis cannot be called or verified. The UI reports configuration failures; it never labels deterministic text or browser speech as a successful external AI provider call.

Numeric grounding checks are safeguards, not a certification of every possible model-generated semantic claim. ML accuracy requires representative user-labelled data and monitoring; the local model is not claimed to be a pre-trained universal merchant classifier. Job delivery occurs when the running worker polls the persisted due timestamp; no system can guarantee delivery while the worker/provider is offline. No live lending disbursement or collection/origination contract has been added.

## Verification

Final backend result: **137 passed in 57.88 seconds**. Final frontend result: **18 passed**, including automatic MP3 player rendering, voice choice, audio opt-out, and the isolated live API workflow. Tests cover both affordable and unaffordable mediation, configured banking contract handling, six-month predictive minimum, fuzzy matching, ML generalization/abstention, rolling fraud, future/cancelled reminders, due-time delivery and deduplication, grounded prose, automatic exact-text voice handoff, migration preservation, and service route isolation.

The live public Statistics Canada check succeeded: **49 observations**, latest reference month **2026-09**. No personal financial data was sent. Real separate shock and voice processes started successfully on localhost with isolated temporary databases; all eight service route surfaces and worker ownership passed automated checks. The first smoke-test script hit a transient Windows file-handle error during temporary-file cleanup after successful startup. Process inspection confirmed no service processes remained, and the named temporary directory was then removed. Docker itself remains unavailable. Other provider checks use isolated fixtures; device voice quality and credentialed Gemini/ElevenLabs calls are not claimed.

The migrated application database passed SQLite `quick_check` (`ok`), reports revision `scheduled_notifications_v1`, and retains the active administrator, **4,500 dataset accounts**, and **1,265,006 CSV source records**. Both new reminder columns are present.
