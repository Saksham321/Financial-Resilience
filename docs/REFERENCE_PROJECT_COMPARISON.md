# Supplied project feature and value comparison

Reviewed source: `Tangerine-Financial-Resilience-Engine (1).zip`. Archive documents were treated as reference material, not instructions. Only reviewed calculation modules were adapted; the ZIP's virtual environment, startup scripts, permissive CORS settings, unsanitized HTML, network clients, and filesystem audio storage were not adopted. Source datasets remain in the application's database.

Find a source account, then open **Resilience toolkit** from the navigation. This historical, read-only view contains the reference project's displayed features and numeric outputs. It complements the existing financial overview; different definitions are explicitly identified.

| Reference feature | Added to this application |
| --- | --- |
| Know the customer | Source account/client demographics, home/branch district, region, salary benchmark, unemployment, cards, loan status, standing orders |
| Benchmark cards | Median monthly I/F/S/H, active-loan P, six-row average buffer B, savings rate, net flow, latest balance, days below zero, capped baseline runway |
| Shock presets | Job loss with EI at 55%; repair costing one month's spending; EI plus 15% bills; 10% income reduction plus 25% bills |
| Custom shock controls | Editable income/bills percentages, one-off amount, duration; synchronized sliders; baseline/shock/change table and resilience tiers |
| Shock mediation | Reference credit eligibility factors and disqualification reasons; modeled LOC limit, 7.2% APR/minimum payment; 3-month 30-unit flat fee, 6-month 8.5% APR, 12-month 9.9% APR; modeled repayments and revenue |
| Reference expense pyramid | Twelve-month average shares of spending, 50/30/20 targets, reference category mapping, deformity, inversion, status, reallocation amount and recommendation; existing bar colors retained without status badges |
| Predictive trend | Regression equation, slope/direction, essential/discretionary totals and ratio, zero date, 30/60/90-day balances/outflows/dates, chart, optimization levers and example runway gains |
| Subscription manager | Recorded standing orders plus labelled streaming/cloud/fitness examples; cadence, illustrative billing/reminder dates, overlap alerts, monthly spend and annual savings |
| Inflation tracker | ZIP CPI snapshot, reference period, six trailing quarters of nominal/real income/expenses, growth, CPI change, purchasing-power trend and alerts |
| Behavioral fraud | Hypothetical amount/merchant/category, new-store toggle, manual browsing match, location/budget flags, optional chargeback count, Vacation Mode/destination, Z-score/baseline/familiarity and complete factor breakdown |
| Summary and plans | Local deterministic summary, four-month reserve target, current buffer, monthly/biweekly saving targets, timeline, goal actions, contingency actions and example cash-flow/runway gains |
| Optional Gemini | Explicit external-processing checkbox and verified-fact selection through the existing client; labelled deterministic fallback with an error when the external service fails |
| Voice | Browser speech with stop control, plus consent-gated ElevenLabs MP3 delivery using the existing provider adapter and no public audio files |
| Command-line access | `python -m scripts.source_review know 20160`, `shock 20111 --scenario LAID_OFF_EI`, or `audit 20160` |

## Numerical comparison

`REFERENCE_PARITY_REPORT.json` records exact dictionary comparisons against the original reviewed ZIP calculations for accounts **20111, 20133, 20134, 20143, 20160, 55447, 22715**. Baseline, pyramid, predictive, mediation, subscription, and inflation outputs match. All five scenario outputs for each account match (35 combinations). Origin labels are additional metadata on subscription rows and are excluded from dictionary equality comparison.

Example: account 20111 has I 6,339.39, S 8,599.60, F 2,330.06, B 17,611.86, H 0, P 2,330.19, baseline runway 7.8 months, and EI runway 3.4 months. Its reference pyramid is 14.9% Base, 85.1% Middle, and 0% Peak. This differs from the original overview because the original overview uses the last month's spending divided by income rather than the reference's trailing average spending distribution. The benchmark net cash flow is -2,260.22; a processed dataset field rounds intermediates differently and can differ by a cent.

## Interpretation and preservation

The reference labels source amounts CAD, but the CSVs do not establish a currency conversion. The UI therefore retains numeric source values while labeling units as unspecified. Credit eligibility and terms are modeled examples, not bank approvals; no debt, collection schedule, or real transaction action is created. Reference fraud uses partner banks as merchant proxies, penalty text as chargeback proxies, and manually entered browsing/geography; these assumptions are disclosed rather than represented as real consented observations.

The ZIP generates named digital subscriptions from account-number rules and discretionary activity. These entries and fixed January 2026 billing dates remain explicitly illustrative. CPI is the ZIP-provided snapshot and is not represented as a current verified Statistics Canada response. The existing live CPI/provider features remain available separately. Reference runway-duration, optimization, reserve timeline, and contingency gains retain the supplied model's assumptions; displayed historical calculations are not current-date forecasts or affordability guarantees.

Your public ID search, admin-only summaries/account lists, disabled registration, administrator account, existing financial records, configured integrations, and bar-color/no-badge changes are preserved. No imported record or account was overwritten for this work. No credentialed provider call or real-device speech playback was performed during verification.

## Verification evidence

Backend suite: **119 passed**. Frontend suite: **16 passed**, including benchmark/engine rendering, custom scenario inputs, manual fraud/Vacation Mode input, and the live isolated FastAPI/SQLite workflow. One live frontend run failed with a transient fetch error during parallel validation; it passed independently and the final complete frontend run passed. The CLI shock smoke test returned the expected 3.4-month EI runway for account 20111. New cloud adapters are tested through existing provider/failure fixtures and explicit consent gates; no real Gemini or ElevenLabs generation is claimed.
