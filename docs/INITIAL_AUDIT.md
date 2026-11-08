# Initial requirements audit

| Existing foundation | Initial status |
| --- | --- |
| JWT/bcrypt registration, login and current-user API | IMPLEMENTED at backend level; no frontend |
| Database sessions, core account/user/audit models, migrations | PARTIALLY IMPLEMENTED; type/constraint and URL bugs |
| Health and tracing | IMPLEMENTED infrastructure; engine registration inaccurate |
| Gemini | PARTIALLY IMPLEMENTED scaffold; unsafe fallback and blocking call |
| Financial engines, frontend, financial workers, other providers | MISSING |

Audit completed before implementation. Existing architecture: Python FastAPI modular monolith, SQLAlchemy async PostgreSQL with local SQLite fallback, JWT/bcrypt authentication, Alembic migrations. No frontend, workers, financial transaction model, or implemented domain engines. Redis/RabbitMQ are container declarations only. Gemini is a scaffold with an unsafe mock fallback and blocking SDK call. Existing readiness lists engines that do not exist. Core banking, underwriting, browsing, notifications, CPI, and voice are absent. No independently deployed microservices exist.

Existing user/accounts/preferences/audit models and auth/health routes are PARTIALLY IMPLEMENTED foundations for the requested product. Existing 14 tests cover foundations only. Initial migration omits model foreign keys and uses CHAR UUIDs on PostgreSQL; configured database URLs are stringified with passwords redacted, breaking real connections.

Every specification bullet below is initially MISSING end-to-end unless indicated otherwise. Final coverage and verification are documented separately.

| Requirement | Initial status |
| --- | --- |
| Detection of incoming and projected financial shocks. | MISSING |
| Retrieval of checking, savings, and available liquid balances. | MISSING |
| Calculation of financial shortfalls. | MISSING |
| Verification of standard credit eligibility. | MISSING |
| Routing to conventional credit or overdraft protection when eligible. | MISSING |
| Generation of alternative installment plans when conventional credit is unavailable. | MISSING |
| Support for 3-month, 6-month, and 12-month repayment periods. | MISSING |
| Calculation of installment amounts, fees, and applicable interest. | MISSING |
| Affordability assessment using projected monthly cash flow. | MISSING |
| Generation of personalized installment offers. | MISSING |
| Push notifications and frontend offer presentation. | MISSING |
| Explicit user acceptance before activating repayment obligations. | MISSING |
| Recording of accepted and rejected offers. | MISSING |
| Analysis of 6–12 months of historical transactions. | MISSING |
| Classification of essential and discretionary expenditures. | MISSING |
| Monthly transaction aggregation. | MISSING |
| Linear regression using the formula: | MISSING |
| Calculation of spending trends and regression slope. | MISSING |
| Financial runway estimation. | MISSING |
| Projected financial balances at 30, 60, and 90 days. | MISSING |
| Estimated date when available funds reach zero. | MISSING |
| Identification of spending categories that can be reduced. | MISSING |
| Personalized financial recommendations. | MISSING |
| Calculation of the estimated impact of recommendations on financial runway. | MISSING |
| Automatic forecast updates when significant financial events occur. | MISSING |
| Merchant transaction history. | MISSING |
| Merchant category familiarity. | MISSING |
| Geographic spending patterns. | MISSING |
| Typical transaction times. | MISSING |
| Historical transaction amounts. | MISSING |
| Shopping cart size analysis. | MISSING |
| User spending budgets. | MISSING |
| Assign a baseline anomaly score of 0.50 when a merchant has no transaction history. | MISSING |
| Update merchant familiarity as additional transactions occur. | MISSING |
| Decrease the current anomaly score by 10% for each qualifying recurring transaction involving the same merchant. | MISSING |
| Apply the reduction multiplicatively. | MISSING |
| Ensure scoring adjustments cannot reduce the score below zero. | MISSING |
| Integrate the browsing-context analysis API. | MISSING |
| Check whether the user has recently viewed products or categories matching the transaction category. | MISSING |
| If a qualifying category match exists, reduce the anomaly score by 0.15. | MISSING |
| Only retrieve browsing information when the user has explicitly granted permission. | MISSING |
| Query historical chargeback reports. | MISSING |
| Add 0.10 to the anomaly score for each chargeback recorded within the previous three months. | MISSING |
| Establish a normal spending area using historical merchant locations and user-configured geographic preferences. | MISSING |
| Detect transactions occurring outside the established spending area. | MISSING |
| Add 0.25 to the anomaly score for qualifying geographic anomalies. | MISSING |
| Compare transaction amounts against the user's applicable spending budget. | MISSING |
| Add 0.10 to the anomaly score when a transaction exceeds the applicable budget. | MISSING |
| New merchant: baseline 0.50. | MISSING |
| Recurring merchant: reduce current score by 10%. | MISSING |
| Matching browsing category: subtract 0.15. | MISSING |
| Each recent chargeback: add 0.10. | MISSING |
| Outside normal spending area: add 0.25. | MISSING |
| Outside spending budget: add 0.10. | MISSING |
| Enable Vacation Mode. | MISSING |
| Specify a vacation destination. | MISSING |
| Specify start and end dates. | MISSING |
| Set a vacation spending budget. | MISSING |
| View total vacation expenditures. | MISSING |
| Track individual vacation transactions. | MISSING |
| View merchant names and spending categories. | MISSING |
| Track merchant geolocation. | MISSING |
| View vacation spending geographically. | MISSING |
| See remaining vacation budget. | MISSING |
| View a summary of spending during the trip. | MISSING |
| Recognize expected spending activity within the designated travel area. | MISSING |
| Adjust geographic anomaly scoring appropriately. | MISSING |
| Continue evaluating merchant, transaction amount, chargeback, and other fraud indicators. | MISSING |
| Associate eligible transactions with the active vacation record. | MISSING |
| Automatic identification of recurring transactions. | MISSING |
| Monthly billing detection using approximately 28–31-day intervals. | MISSING |
| Annual subscription detection. | MISSING |
| Prediction of upcoming billing dates. | MISSING |
| Notifications three days before expected billing dates. | MISSING |
| Subscription categorization. | MISSING |
| Detection of overlapping subscriptions. | MISSING |
| Identification of multiple streaming subscriptions. | MISSING |
| Identification of multiple cloud storage subscriptions. | MISSING |
| Detection of combined fitness and wellness spending exceeding $150 per month. | MISSING |
| Subscription management interface. | MISSING |
| Subscription cancellation status tracking. | MISSING |
| Duplicate subscription prevention. | MISSING |
| Prevention of duplicate notifications. | MISSING |
| Quarterly income aggregation. | MISSING |
| Quarterly expenditure aggregation. | MISSING |
| Retrieval of Consumer Price Index data from Statistics Canada. | MISSING |
| Inflation adjustment of historical income. | MISSING |
| Inflation adjustment of historical expenses. | MISSING |
| Calculation of real income growth. | MISSING |
| Calculation of real expense growth. | MISSING |
| Quarter-over-quarter comparisons. | MISSING |
| Identification of declining purchasing power. | MISSING |
| Overspending alerts. | MISSING |
| Wage stagnation alerts. | MISSING |
| Real expense growth exceeds real income growth and real expenses exceed real income. | MISSING |
| Real income growth is negative. | MISSING |
| Household bills. | MISSING |
| Loan payments. | MISSING |
| Insurance. | MISSING |
| Groceries. | MISSING |
| Transportation. | MISSING |
| Basic utilities. | MISSING |
| Entertainment. | MISSING |
| Card withdrawals. | MISSING |
| Discretionary and applicable unclassified spending. | MISSING |
| Automatic expense categorization. | MISSING |
| Calculation of actual spending ratios relative to monthly income. | MISSING |
| Comparison against target ratios. | MISSING |
| Expense Pyramid Deformity Score. | MISSING |
| Inverted Pyramid detection. | MISSING |
| Personalized spending reallocation recommendations. | MISSING |
| Visual representation of actual versus target ratios. | MISSING |
| Integration with the Gemini API. | MISSING |
| Aggregation of financial insights from the relevant engines. | MISSING |
| Personalized financial health summaries. | MISSING |
| Spending habit explanations. | MISSING |
| Financial runway explanations. | MISSING |
| Shock scenario analysis. | MISSING |
| Personalized financial recommendations. | MISSING |
| Financial contingency plans. | MISSING |
| Conversational and empathetic output. | MISSING |
| Account balances. | MISSING |
| Transaction history. | MISSING |
| Interest rates. | MISSING |
| Credit eligibility. | MISSING |
| Financial projections. | MISSING |
| User financial information. | MISSING |
| Integration with the ElevenLabs Text-to-Speech API. | MISSING |
| Conversion of Gemini-generated summaries into audio. | MISSING |
| Configurable professional and empathetic voice profiles. | MISSING |
| MP3 audio generation. | MISSING |
| Secure audio delivery or streaming. | MISSING |
| Frontend playback. | MISSING |
| Play, pause, and replay functionality. | MISSING |
| Appropriate loading and error states. | MISSING |
| Services exchange the correct data. | MISSING |
| APIs use consistent schemas. | MISSING |
| Authentication and authorization are enforced. | MISSING |
| User IDs are consistent across services. | MISSING |
| Financial data is not duplicated unnecessarily. | MISSING |
| Background jobs execute correctly. | MISSING |
| Event-driven workflows function correctly. | MISSING |
| Failed integrations are handled gracefully. | MISSING |
| Duplicate events do not create duplicate financial operations. | MISSING |
| Logs and monitoring are available. | MISSING |
| Services can be independently maintained and scaled. | MISSING |
| View their overall financial health. | MISSING |
| View available liquidity and financial runway. | MISSING |
| Understand incoming financial shocks. | MISSING |
| Compare installment repayment options. | MISSING |
| Accept or reject financial offers. | MISSING |
| View projected financial balances. | MISSING |
| Receive personalized financial recommendations. | MISSING |
| View transaction fraud alerts. | MISSING |
| Understand why a transaction was flagged. | MISSING |
| Enable and manage Vacation Mode. | MISSING |
| View vacation spending and transaction locations. | MISSING |
| View recurring subscriptions. | MISSING |
| Receive upcoming subscription notifications. | MISSING |
| Identify redundant subscriptions. | MISSING |
| View inflation-adjusted purchasing power. | MISSING |
| View real income and expense trends. | MISSING |
| View their Visual Expense Pyramid. | MISSING |
| Understand spending imbalances. | MISSING |
| Read AI-generated financial summaries. | MISSING |
| Listen to audio financial summaries. | MISSING |
| Unit tests for financial calculations. | MISSING |
| Integration tests for microservice communication. | MISSING |
| API endpoint tests. | MISSING |
| Database model and migration tests. | MISSING |
| Authentication and authorization tests. | MISSING |
| Fraud scoring tests for every individual adjustment. | MISSING |
| Vacation Mode tests. | MISSING |
| Subscription detection tests. | MISSING |
| Forecasting tests. | MISSING |
| Inflation calculation tests. | MISSING |
| Expense Pyramid tests. | MISSING |
| Gemini integration tests. | MISSING |
| ElevenLabs integration tests. | MISSING |
| Frontend interaction tests. | MISSING |
| Users with no transaction history. | MISSING |
| New merchants. | MISSING |
| Missing browsing permissions. | MISSING |
| Missing geolocation. | MISSING |
| Multiple chargebacks. | MISSING |
| Negative or zero account balances. | MISSING |
| Zero or missing income. | MISSING |
| Duplicate transactions. | MISSING |
| Duplicate subscription notifications. | MISSING |
| Failed external API requests. | MISSING |
| Incomplete historical financial data. | MISSING |
| Already implemented. | MISSING |
| Partially implemented. | MISSING |
| Missing. | MISSING |
| Core Banking API. | MISSING |
| Underwriting Service. | MISSING |
| Statistics Canada API. | MISSING |
| Gemini API. | MISSING |
| ElevenLabs API. | MISSING |
| Browsing Context API. | MISSING |
| Notification Service. | MISSING |
