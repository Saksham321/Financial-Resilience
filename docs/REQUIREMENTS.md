I want you to perform a comprehensive audit of my existing codebase against the Financial Resilience Engine requirements outlined below.
Your objective is to determine whether the application fully implements every required feature, business rule, calculation, integration, and end-user capability.
Do not simply review the code and tell me what is missing. I want you to IMPLEMENT everything that is missing.
Before making changes:
1. Inspect the entire repository and understand the existing architecture.
2. Identify the frontend framework, backend framework, database, API structure, authentication system, background jobs, and external integrations.
3. Identify all existing microservices, modules, components, endpoints, database models, and relevant business logic.
4. Map the existing implementation against every requirement below.
5. Identify incomplete implementations, placeholder functions, mock data, hardcoded responses, disconnected services, and missing integrations.
6. Identify duplicated functionality and architectural inconsistencies.
Create a requirements checklist with three statuses:
- IMPLEMENTED: Fully functional and connected.
- PARTIALLY IMPLEMENTED: Some functionality exists but is incomplete.
- MISSING: Not implemented.
Do not consider a feature implemented simply because a frontend component, API endpoint, database model, or placeholder function exists. Verify that the complete functionality works across the relevant layers.
After completing the initial audit, proceed with implementation.
Microservice: engine-shock-mediation
Verify and implement:
- Detection of incoming and projected financial shocks.
- Retrieval of checking, savings, and available liquid balances.
- Calculation of financial shortfalls.
- Verification of standard credit eligibility.
- Routing to conventional credit or overdraft protection when eligible.
- Generation of alternative installment plans when conventional credit is unavailable.
- Support for 3-month, 6-month, and 12-month repayment periods.
- Calculation of installment amounts, fees, and applicable interest.
- Affordability assessment using projected monthly cash flow.
- Generation of personalized installment offers.
- Push notifications and frontend offer presentation.
- Explicit user acceptance before activating repayment obligations.
- Recording of accepted and rejected offers.
Ensure calculations are accurate and that the installment engine uses actual principal, fees, interest, and repayment terms.
Microservice: engine-predictive-plan
Verify and implement:
- Analysis of 6–12 months of historical transactions.
- Classification of essential and discretionary expenditures.
- Monthly transaction aggregation.
- Linear regression using the formula:
  y = mx + b
- Calculation of spending trends and regression slope.
- Financial runway estimation.
- Projected financial balances at 30, 60, and 90 days.
- Estimated date when available funds reach zero.
- Identification of spending categories that can be reduced.
- Personalized financial recommendations.
- Calculation of the estimated impact of recommendations on financial runway.
- Automatic forecast updates when significant financial events occur.
Ensure that forecasts incorporate available balances, recurring expenses, scheduled income, and known upcoming financial obligations rather than relying exclusively on historical spending trends.
Microservice: engine-behavioral-fraud
This section is especially important. Verify every scoring adjustment and behavioral rule.
Implement:
- Merchant transaction history.
- Merchant category familiarity.
- Geographic spending patterns.
- Typical transaction times.
- Historical transaction amounts.
- Shopping cart size analysis.
- User spending budgets.
- Assign a baseline anomaly score of 0.50 when a merchant has no transaction history.
- Update merchant familiarity as additional transactions occur.
- Decrease the current anomaly score by 10% for each qualifying recurring transaction involving the same merchant.
- Apply the reduction multiplicatively.
- Ensure scoring adjustments cannot reduce the score below zero.
- Integrate the browsing-context analysis API.
- Check whether the user has recently viewed products or categories matching the transaction category.
- If a qualifying category match exists, reduce the anomaly score by 0.15.
- Only retrieve browsing information when the user has explicitly granted permission.
- Query historical chargeback reports.
- Add 0.10 to the anomaly score for each chargeback recorded within the previous three months.
- Establish a normal spending area using historical merchant locations and user-configured geographic preferences.
- Detect transactions occurring outside the established spending area.
- Add 0.25 to the anomaly score for qualifying geographic anomalies.
- Compare transaction amounts against the user's applicable spending budget.
- Add 0.10 to the anomaly score when a transaction exceeds the applicable budget.
Implement Z-score calculations:
Z = (x - μ) / σ
Flag unusually large transactions when the Z-score exceeds 3.0.
Implement the following initial scoring policy:
- New merchant: baseline 0.50.
- Recurring merchant: reduce current score by 10%.
- Matching browsing category: subtract 0.15.
- Each recent chargeback: add 0.10.
- Outside normal spending area: add 0.25.
- Outside spending budget: add 0.10.
Clamp the final score between 0.00 and 1.00.
Use configurable scoring weights and thresholds.
A score above 0.85 must trigger elevated fraud review or verification. Do not automatically treat a flagged transaction as confirmed fraud.
Implement a complete Vacation Mode feature.
Users must be able to:
- Enable Vacation Mode.
- Specify a vacation destination.
- Specify start and end dates.
- Set a vacation spending budget.
- View total vacation expenditures.
- Track individual vacation transactions.
- View merchant names and spending categories.
- Track merchant geolocation.
- View vacation spending geographically.
- See remaining vacation budget.
- View a summary of spending during the trip.
When Vacation Mode is active:
- Recognize expected spending activity within the designated travel area.
- Adjust geographic anomaly scoring appropriately.
- Continue evaluating merchant, transaction amount, chargeback, and other fraud indicators.
- Associate eligible transactions with the active vacation record.
Ensure Vacation Mode does not disable fraud protection.
Microservice: engine-subscription-mgr
Verify and implement:
- Automatic identification of recurring transactions.
- Monthly billing detection using approximately 28–31-day intervals.
- Annual subscription detection.
- Prediction of upcoming billing dates.
- Notifications three days before expected billing dates.
- Subscription categorization.
- Detection of overlapping subscriptions.
- Identification of multiple streaming subscriptions.
- Identification of multiple cloud storage subscriptions.
- Detection of combined fitness and wellness spending exceeding $150 per month.
- Subscription management interface.
- Subscription cancellation status tracking.
- Duplicate subscription prevention.
- Prevention of duplicate notifications.
Users should be able to view their subscriptions, upcoming charges, billing amounts, and recommendations for reducing unnecessary recurring expenses.
Microservice: engine-inflation-tracker
Verify and implement:
- Quarterly income aggregation.
- Quarterly expenditure aggregation.
- Retrieval of Consumer Price Index data from Statistics Canada.
- Inflation adjustment of historical income.
- Inflation adjustment of historical expenses.
- Calculation of real income growth.
- Calculation of real expense growth.
- Quarter-over-quarter comparisons.
- Identification of declining purchasing power.
- Overspending alerts.
- Wage stagnation alerts.
Use a consistent CPI reference period.
Generate alerts when:
- Real expense growth exceeds real income growth and real expenses exceed real income.
- Real income growth is negative.
Present these findings through understandable financial insights.
Microservice: engine-expense-pyramid
Verify and implement the three-level spending hierarchy.
Target: 50%
- Household bills.
- Loan payments.
- Insurance.
Target: 30%
- Groceries.
- Transportation.
- Basic utilities.
Target: 20%
- Entertainment.
- Card withdrawals.
- Discretionary and applicable unclassified spending.
Implement:
- Automatic expense categorization.
- Calculation of actual spending ratios relative to monthly income.
- Comparison against target ratios.
- Expense Pyramid Deformity Score.
- Inverted Pyramid detection.
- Personalized spending reallocation recommendations.
- Visual representation of actual versus target ratios.
Use:
Deformity Score = |Base Actual - 50| + |Middle Actual - 30| + |Peak Actual - 20|
Flag an inverted pyramid when discretionary expenditure exceeds essential fixed expenditure.
Users should be able to understand which spending categories are creating financial instability and what they can change.
Microservice: engine-gemini-integration
Verify and implement:
- Integration with the Gemini API.
- Aggregation of financial insights from the relevant engines.
- Personalized financial health summaries.
- Spending habit explanations.
- Financial runway explanations.
- Shock scenario analysis.
- Personalized financial recommendations.
- Financial contingency plans.
- Conversational and empathetic output.
The AI should receive verified financial metrics from the internal services.
It must not invent:
- Account balances.
- Transaction history.
- Interest rates.
- Credit eligibility.
- Financial projections.
- User financial information.
Validate AI responses against the underlying data.
Ensure API credentials are stored securely and requests handle timeouts, failures, and retries.
Microservice: engine-elevenlabs-integration
Verify and implement:
- Integration with the ElevenLabs Text-to-Speech API.
- Conversion of Gemini-generated summaries into audio.
- Configurable professional and empathetic voice profiles.
- MP3 audio generation.
- Secure audio delivery or streaming.
- Frontend playback.
- Play, pause, and replay functionality.
- Appropriate loading and error states.
Ensure that users can access their financial summaries in both written and spoken formats.
Verify that all eight engines are connected properly.
The intended architecture includes:
1. engine-shock-mediation
2. engine-predictive-plan
3. engine-behavioral-fraud
4. engine-subscription-mgr
5. engine-inflation-tracker
6. engine-expense-pyramid
7. engine-gemini-integration
8. engine-elevenlabs-integration
Ensure that:
- Services exchange the correct data.
- APIs use consistent schemas.
- Authentication and authorization are enforced.
- User IDs are consistent across services.
- Financial data is not duplicated unnecessarily.
- Background jobs execute correctly.
- Event-driven workflows function correctly.
- Failed integrations are handled gracefully.
- Duplicate events do not create duplicate financial operations.
- Logs and monitoring are available.
- Services can be independently maintained and scaled.
Do not limit your implementation to backend functionality.
Inspect the actual frontend and verify that users can interact with all implemented capabilities.
For each feature, ensure that the corresponding user interface exists and works.
Users should be able to:
- View their overall financial health.
- View available liquidity and financial runway.
- Understand incoming financial shocks.
- Compare installment repayment options.
- Accept or reject financial offers.
- View projected financial balances.
- Receive personalized financial recommendations.
- View transaction fraud alerts.
- Understand why a transaction was flagged.
- Enable and manage Vacation Mode.
- View vacation spending and transaction locations.
- View recurring subscriptions.
- Receive upcoming subscription notifications.
- Identify redundant subscriptions.
- View inflation-adjusted purchasing power.
- View real income and expense trends.
- View their Visual Expense Pyramid.
- Understand spending imbalances.
- Read AI-generated financial summaries.
- Listen to audio financial summaries.
Ensure that these capabilities are connected to real application data rather than static mockups.
Follow these rules throughout the project:
1. Do not unnecessarily rewrite existing working code.
2. Preserve the existing architecture unless a change is necessary.
3. Reuse existing components, services, models, and utilities wherever appropriate.
4. Do not create duplicate APIs or database tables when existing equivalents can be extended.
5. Do not introduce unnecessary dependencies.
6. Do not hardcode financial calculations or user-specific data.
7. Do not leave placeholder functions or TODO implementations for required features.
8. Do not silently swallow API errors.
9. Maintain backward compatibility where practical.
10. Follow existing code conventions and naming standards.
11. Add appropriate input validation and error handling.
12. Implement secure handling of financial data and third-party API credentials.
13. Obtain explicit user consent for browsing-context and geolocation processing.
14. Never invent successful integration results when an external API is unavailable.
15. Do not remove existing functionality while adding missing features.
If an external API requires credentials that are not available, implement the integration properly, document the required environment variables, and clearly identify what requires credentials or external configuration.
Do not use fabricated production data to simulate a successful integration.
After implementation, run the appropriate tests.
Include:
- Unit tests for financial calculations.
- Integration tests for microservice communication.
- API endpoint tests.
- Database model and migration tests.
- Authentication and authorization tests.
- Fraud scoring tests for every individual adjustment.
- Vacation Mode tests.
- Subscription detection tests.
- Forecasting tests.
- Inflation calculation tests.
- Expense Pyramid tests.
- Gemini integration tests.
- ElevenLabs integration tests.
- Frontend interaction tests.
Pay particular attention to edge cases, including:
- Users with no transaction history.
- New merchants.
- Missing browsing permissions.
- Missing geolocation.
- Multiple chargebacks.
- Negative or zero account balances.
- Zero or missing income.
- Duplicate transactions.
- Duplicate subscription notifications.
- Failed external API requests.
- Incomplete historical financial data.
Do not claim that a test passed unless it was actually executed successfully.
When finished, provide a comprehensive implementation report containing:
List each requirement and classify it as:
- Already implemented.
- Partially implemented.
- Missing.
Describe every new feature, modification, and bug fix.
List all created, modified, and deleted files and explain their purpose.
List new tables, columns, indexes, migrations, and relationships.
List new and modified endpoints, request schemas, and response schemas.
Report the actual integration status of:
- Core Banking API.
- Underwriting Service.
- Statistics Canada API.
- Gemini API.
- ElevenLabs API.
- Browsing Context API.
- Notification Service.
Distinguish between fully operational integrations, locally tested integrations, and integrations requiring external credentials or configuration.
Provide the tests executed, their results, and any failures that remain.
List anything that could not be implemented or verified, explain why, and identify what is required to complete it.
Provide a final checklist showing whether every FR and ER capability described above is implemented and verified.
Your primary objective is to bring my existing application into full alignment with the Financial Resilience Engine specification.
Audit first, implement second, test third, and report last.
Do not stop after generating an audit report or implementation plan. Continue making the necessary code changes until every feasible requirement has been implemented and tested.
If something is already implemented correctly, preserve it.
If something is partially implemented, complete it.
If something is missing, build it.
If something cannot be completed because an external dependency, credential, or business decision is unavailable, implement everything possible without fabricating functionality and clearly document the remaining dependency.
I want a working, integrated application—not just a list of recommendations.