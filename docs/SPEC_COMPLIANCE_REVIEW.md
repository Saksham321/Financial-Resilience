# System architecture specification review

**Follow-up:** Code gaps from this audit have now been implemented. See [requirement completion](REQUIREMENT_COMPLETION.md) for the current behavior, tests, configuration dependencies, and deployment limits. The findings below describe the pre-completion state.

Reviewed November 7, 2026 against [the newly supplied specification](SYSTEM_ARCHITECTURE_SPEC.md). This is a fresh code/configuration audit, not a restatement of the earlier feature checklist. No implementation was changed for this audit. Documents supplied as attachments were treated as requirements to compare, not as instructions to execute.

**Overall: not all requirements are met.** Core deterministic calculations and much of the local workflow exist. Missing algorithms, literal API/schema differences, unconfigured integrations, and the distinction between personal financial workflows and reference simulations prevent a full compliance claim.

Status vocabulary: **MET LOCALLY** = implemented behavior with local tests; **PARTIAL** = material portions exist but scope, configuration, or contract gaps remain; **MISSING** = the specified implementation is absent; **UNVERIFIED LIVE** = local client/contract evidence does not establish provider success. A passing test is not a production certification.

## Architecture and inputs

| Requirement | Status | Evidence and limits |
| --- | --- | --- |
| Named financial engines | MET LOCALLY | Modules and routes cover all eight areas; see app/engines, app/integrations, and app/reference_engines. |
| Independently operating microservices | PARTIAL | app/api/router.py mounts the engines inside one FastAPI application. It is a modular monolith, not eight separately deployed services. |
| Auth-context user IDs and Decimal financial inputs | MET LOCALLY for personal workflows | app/core/dependencies.py and app/engines/schemas.py use authenticated UUID ownership and Decimal money. Public source-account lookup intentionally uses imported account IDs and does not authenticate an actual banking customer. |
| Live financial data and external source integrations | PARTIAL / UNVERIFIED LIVE | Adapters exist, but the current banking/underwriting/browsing/notification URLs and keys are absent. Source CSVs are historical reference records, not live banking data. |

## 1. Shock mediation and revenue

| Spec requirement | Status | Evidence and limits |
| --- | --- | --- |
| Receive shock and identify authenticated user | MET LOCALLY | POST /api/v1/finance/shocks; user ownership, validation, and idempotency in app/engines/service.py create_shock. |
| Fetch checking/savings/immediate cash buffer from Core Banking API for each mediation | PARTIAL | liquidity sums stored active CAD checking/savings snapshots. Banking sync is a separate API operation, not a live fetch inside every mediation. No separate CASH account type is supported. Banking adapter currently unconfigured. |
| Compute positive shortfall and recognize sufficient buffer | MET LOCALLY | create_shock uses max(0, shock amount minus projected available balance at due date). This extends the simple current-buffer formula for projected shocks. |
| Obtain eligibility from underwriting and route eligible users to conventional credit | PARTIAL / UNVERIFIED LIVE | Validated underwriting adapter and conventional_credit/eligibility_unknown routes exist. No configured underwriting provider or actual loan origination flow. The reference toolkit's modeled eligibility is not underwriting evidence. |
| Generate 3/6/12-month interest/fee plans when standard credit is restricted | PARTIAL | generate_offers and installment implement these terms after a verified denial. Current approved fee/rate settings are absent. Reference example terms remain simulations. |
| Ensure suggested repayments keep monthly cash flow positive | PARTIAL | Capacity is checked and unaffordable acceptance is rejected. The proposal generator still returns unaffordable options marked affordable=false rather than suggesting only positive-cash-flow plans. No forecast guarantees financial outcomes. |
| Offer UI and push notification | PARTIAL | Persistent in-app notices and offers exist. External notification delivery is implemented but unconfigured/unverified. Browser device notifications require an open page and permission. |
| Log buffer-sufficient and intervention outcomes | MET LOCALLY | Stored Shock/routing records, scheduled flows, audit/financial decisions, and offer acceptance/rejection tracking exist. |
| Exact POST /api/v1/shocks/mediate and proposed request/response JSON | MISSING as a literal contract | Published OpenAPI does not contain that path. Implemented paths are /api/v1/finance/shocks and /api/v1/source-review/{account_id}/simulate. Field names and nested response structures differ. |

The sample user_id string in the specification is not a UUID although the input table says UUID. Its repayment numbers are examples, not universally valid outputs for every amount/term. A contract decision is needed before treating those examples as exact fixtures.

## 2. Predictive and actionable planning

| Spec requirement | Status | Evidence and limits |
| --- | --- | --- |
| Monthly aggregation of 6–12 months of outflows | MET LOCALLY with qualification | forecast uses up to twelve completed months and flags fewer than six; it still produces limited-history estimates rather than requiring six observations. |
| Linear regression y=mx+b and specified slope | MET LOCALLY | regression and forecast in app/engines/calculations.py; financial_rules tests verify regression and calendar projections. |
| ML tagging pipeline for essential/discretionary categorization | MISSING | classify uses supplied categories, merchant history, and keyword rules. Installed ML dependencies do not establish a trained or invoked tagging model. |
| 30/60/90-day balances, financial runway and depletion date | MET LOCALLY | Personal forecasts and source-account analysis expose these values and charts; historical reference dates are labelled. |
| Contextual actions with parametric savings/runway impact | MET LOCALLY, reference gains illustrative | Personal forecast recalculates estimated impacts. Some ZIP reference action gains are fixed illustrative values, not independently forecast improvements. |
| Exact output schema with user_id/forecast/action_plan fields | PARTIAL | Equivalent values exist, but the personal dashboard schema differs. The ZIP reference predictive output has a similar shape and uses acc_ identifiers rather than authenticated UUIDs. |

## 3. Behavioral fraud and Vacation Mode

| Spec requirement | Status | Evidence and limits |
| --- | --- | --- |
| Receive transaction, check permissions, retrieve baseline | MET LOCALLY for personal ingestion | ingest validates ownership and processing consent before browsing/geographic use. Reference fraud inputs are hypothetical and do not retrieve browsing or location data. |
| Rolling 90-day category/geography/time baseline | PARTIAL | Personal ingest uses prior transactions without a strict 90-day filter. Reference fraud uses the last 60 rows, not 90 days. There is no full rolling category/time/geography matrix as specified. |
| Merchant category weighted/binary risk contribution | PARTIAL | Category familiarity counts are returned, but the personal final score does not incorporate category-distribution anomaly weight. Reference category is largely used for a browsing match. |
| Cart/amount Z-score, Z>3 anomaly | MET LOCALLY | Z-scores and review flags exist; time/cart anomalies are reported. Time-of-day and cart-count flags do not themselves alter the personal numeric score. |
| New merchant 0.50 and multiplicative 10% recurring reductions | MET LOCALLY in personal engine | anomaly implements these weights for qualifying recurring transactions. The copied reference model has a different familiar baseline and caps recurrence at five visits; it must not be used as proof of this exact rule. |
| Browsing API with consent and recent-category reduction of 0.15 | PARTIAL / UNVERIFIED LIVE | Personal adapter and 72-hour recency handling exist, but no browsing provider is configured. Reference toggle is a manual assumption only. |
| String similarity/Jaro-Winkler-like matching | MISSING | providers.browsing compares casefolded category strings for exact equality; reference fraud also uses exact category equality. No fuzzy matcher is implemented. |
| Actual chargeback reports from previous three months, +0.10 each | MET LOCALLY in personal engine | Chargeback records and calendar-three-month filtering exist. Reference penalty text is only a disclosed proxy, not actual chargeback reports. |
| Normal spending-area detection +0.25 | MET LOCALLY for consented personal records | Home/history coordinates and distance thresholds are checked. Real provider ingestion/geolocation quality remains external. |
| Budget overrun +0.10 | MET LOCALLY | Category monthly budgets include already recorded spending before evaluating the incoming transaction. |
| Clamp 0–1 and flag scores >0.85 | MET LOCALLY with policy qualification | Personal score is clamped; score >0.85 triggers review. A separate large-amount Z-score can also trigger review below 0.85, so the behavior is broader than a strict score-only pipeline. No real payment authorization/blocking integration exists. |
| Vacation expenses and store geolocation tracking | MET LOCALLY in personal workflow | Dates, destination, budget, eligible transaction association, totals, remaining budget, and coordinate map exist. The reference checkbox alone supplies no trip ledger or actual geolocation. |

## 4. Proactive subscriptions

| Spec requirement | Status | Evidence and limits |
| --- | --- | --- |
| Monthly 28–31 day and annual recurring detection | MET LOCALLY in personal engine | detect_subscriptions checks intervals and amount stability, with deduplication and cancellation state. |
| Scheduled notification three days before billing | PARTIAL | refresh creates a deduplicated reminder during days 0–3 before billing; the periodic worker retries delivery. This is a polling window, not a persisted exact T−3 scheduled event. External push provider is unconfigured. |
| Streaming/cloud overlap at >=2 and fitness/wellness >150 monthly | MET LOCALLY | Personal category grouping and wellness threshold exist. Reference example overlap demonstrations also exist, with synthetic services labelled. |
| Exact subscription state fields and overlap ID list | PARTIAL | Core Subscription contains merchant, category, amount, cadence, next_billing and status; notices are separate. It does not expose the exact required notification_scheduled_for/overlapping_subscription_ids schema in the personal workflow. Reference entries have example fields and dates, not real scheduled pushes. |

## 5. Inflation and real wage analysis

| Spec requirement | Status | Evidence and limits |
| --- | --- | --- |
| Aggregate income/expenses quarterly and use CPI | MET LOCALLY | inflation and the CPI persistence/refresh endpoint implement these calculations. Missing CPI and incomplete transaction quarters are disclosed. |
| Retrieve monthly CPI from StatCan | IMPLEMENTED / NOT REPROBED LIVE | fetch_cpi and contract tests exist. Prior project notes record a public live probe; this audit does not repeat or certify current service availability. |
| Fetch exactly the trailing four quarters | PARTIAL | Personal inflation returns all available quarters; reference model returns six. The exact four-quarter window is not enforced. |
| Consistent real income/expenses and QoQ growth | MET LOCALLY | Personal model uses a consistent latest CPI reference and guards missing/consecutive quarters. Reference model uses the ZIP's separate historical snapshot. |
| Overspending and wage-stagnation conditions | MET LOCALLY | Personal code applies both specified comparisons to eligible complete quarters; tests exercise alert/missing-data behavior. |
| Reference toolkit's CPI as a live StatCan source | NOT MET; intentionally disclosed | The toolkit uses the ZIP snapshot. It cannot substitute for live CPI integration evidence. |

## 6. Expense pyramid

| Spec requirement | Status | Evidence and limits |
| --- | --- | --- |
| Base/Middle/Peak categories and 50/30/20 targets | PARTIAL | Core tier targets are correct. Exact input labels household_bills, loan_payments, and transit are not canonicalized to the recognized spaced/normalized labels and can fall into Peak. Public source data also lacks reliable groceries/transit classifications. |
| Actual percentages relative to money_in | MET LOCALLY in core overview | pyramid divides tier spend by income. ZIP reference pyramid divides trailing-average tier spend by total spending; it is explicitly a different model and does not satisfy this requirement. |
| Sum of absolute deviations and inverted Peak>Base flag | MET LOCALLY for classified core data | Core formula and inversion are correct; source overview suppresses a complete health score when material amounts are unclassified. Reference deformity additionally scales/caps the score, unlike this specification. |
| Visual status and proposed reallocation UI payload | PARTIAL | Core shows amounts, ratios, score, inversion, and recommendations, but not the exact visual_status/proposed_rearrangement schema. Reference output includes those fields with different formulas/category assumptions. |

## 7. Gemini summaries and planning

| Spec requirement | Status | Evidence and limits |
| --- | --- | --- |
| Aggregate predictive/pyramid/shock metrics and selected scenario | MET LOCALLY for personal summaries; partial reference context | Personal create_summary aggregates engine output and optional hypothetical projections. Reference external prompt includes baseline metric facts and the scenario summary, not all predictive/pyramid/mediation outputs as structured context. |
| Construct prompt and call Gemini | IMPLEMENTED / CURRENTLY UNCONFIGURED | Async Gemini client and validated JSON responses exist. GEMINI_API_KEY is absent in this environment; no real AI-generated result is established. |
| Generate highly personalized conversational summary and action plan | PARTIAL | Gemini selects verified facts and pre-approved phrases/actions rather than freely generating the full plan. Reference goal/backup plans are deterministic calculations/templates. These must not be described as Gemini-generated without a successful call. |
| Return summary to UI | MET LOCALLY | Stored personal summaries and reference briefing panels render the text, source label, goals and backup plan. |
| Automatically pass finalized Gemini text to ElevenLabs | PARTIAL | Both user-triggered audio paths can use finalized text, but generation and TTS require separate actions. No automatic Gemini-success-to-TTS orchestration is wired. |

## 8. ElevenLabs vocal summaries

| Spec requirement | Status | Evidence and limits |
| --- | --- | --- |
| Receive finalized summary and choose professional/empathetic voice | PARTIAL | Personal audio supports both profiles and stored final text. Current professional voice ID exists; empathetic voice ID is absent. Source toolkit currently requests professional voice only. |
| Call ElevenLabs with financial text | IMPLEMENTED / CURRENTLY UNCONFIGURED | providers.speech implements this client and validates audio response. ELEVENLABS_API_KEY is absent; no live synthesis was performed. |
| Deliver MP3 to client for playback | MET LOCALLY with fixture evidence | audio/mpeg responses, private personal asset retrieval, no-store headers, and client audio controls exist. Real audio quality/device playback remains unverified. |
| Browser Read summary aloud satisfies ElevenLabs requirement | NO | Browser speech is a fallback/accessibility feature. It is not an ElevenLabs API call or proof of AI voice integration success. |

## Current configuration evidence

Only booleans were inspected; no secrets were printed. Banking, underwriting, browsing and external notifications have neither URLs nor keys configured. Gemini and ElevenLabs API keys are absent. Personal installment annual rate and fee are unset. A professional voice ID is configured; an empathetic voice ID is not. Presence of an adapter or voice ID alone is not live success.

## Verification and next acceptance gates

Current executed results: **119 backend tests passed in 46.35 seconds** (`python -m pytest -q --tb=short`), and **16 frontend tests passed** (`npm.cmd test`), including the isolated live API workflow. OpenAPI confirmed that `/api/v1/shocks/mediate` is absent. A direct category probe confirmed `household_bills`, `loan_payments`, and `transit` each map to Peak, while the corresponding recognized labels map to Base/Middle. Configuration booleans confirmed the missing external credentials and lending terms described above. No production records were changed and no external provider requests were made. Tests use isolated data and fixture providers; passing them does not close the missing ML/fuzzy-baseline/contract/orchestration requirements.

Priority acceptance gates are: decide the required public contract; implement the ML categorizer and category aliases; complete the rolling category/time/geography fraud baseline and string matching; enforce the desired affordable-offer/reminder/quarter-window policies; wire the finalized Gemini-to-TTS flow; then configure and verify banking, underwriting, browsing, notifications, Gemini and ElevenLabs using the actual agreed provider contracts. Decide separately whether independently deployed microservices are required.
