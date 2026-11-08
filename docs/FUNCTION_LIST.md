# Financial Resilience Engine — Complete Function List

Below is a consolidated list of the functions your Financial Resilience Engine should contain, organized by microservice. These are the individual capabilities that developers should implement.

## 1. Shock Mediation & Revenue Generation

`engine-shock-mediation`

1. `receiveFinancialShock()` – Receive an incoming or projected financial shock.
2. `retrieveLiquidBalance()` – Retrieve checking, savings, and available cash balances.
3. `calculateFinancialShortfall()` – Calculate the difference between the shock amount and available liquidity.
4. `checkCreditEligibility()` – Determine whether the user qualifies for conventional credit.
5. `routeCreditApplication()` – Redirect eligible users to standard credit or overdraft protection.
6. `evaluateInstallmentEligibility()` – Determine whether an alternative installment plan can be offered.
7. `generateInstallmentOptions()` – Generate 3-, 6-, and 12-month repayment options.
8. `calculateMonthlyInstallment()` – Calculate monthly repayment amounts.
9. `calculateInterestAndFees()` – Calculate applicable interest, APR, and flat fees.
10. `evaluateRepaymentAffordability()` – Assess whether repayments are compatible with projected cash flow.
11. `generateInstallmentOffer()` – Create a personalized repayment proposal.
12. `sendShockNotification()` – Notify the user about the financial shortfall and available options.
13. `acceptInstallmentOffer()` – Process the user's acceptance.
14. `rejectInstallmentOffer()` – Record the user's rejection.
15. `recordShockIntervention()` – Maintain an audit record of the intervention.

## 2. Predictive & Actionable Financial Planning

`engine-predictive-plan`

1. `retrieveTransactionHistory()` – Retrieve 6–12 months of financial transactions.
2. `categorizeTransactions()` – Classify transactions into essential and discretionary spending.
3. `aggregateMonthlyIncome()` – Calculate monthly incoming funds.
4. `aggregateMonthlyExpenses()` – Calculate monthly outgoing funds.
5. `calculateSpendingTrend()` – Apply linear regression to identify spending trends.
6. `calculateRegressionSlope()` – Calculate the monthly spending trend slope.
7. `forecastFutureExpenses()` – Project future expenditure.
8. `projectFutureBalances()` – Estimate balances at 30, 60, and 90 days.
9. `calculateFinancialRunway()` – Estimate how many days available funds will last.
10. `predictZeroBalanceDate()` – Estimate when available funds will reach zero.
11. `identifySpendingReductionOpportunities()` – Identify categories where spending can be reduced.
12. `generateFinancialRecommendations()` – Generate personalized financial recommendations.
13. `calculateRecommendationImpact()` – Estimate the financial impact of recommended actions.
14. `calculateRunwayExtension()` – Estimate additional financial runway from spending reductions.
15. `updateFinancialForecast()` – Recalculate forecasts when significant financial changes occur.

## 3. Behavioral Fraud Risk Engine

`engine-behavioral-fraud`

1. `receivePendingTransaction()` – Receive an incoming transaction for evaluation.
2. `checkUserPermissions()` – Verify permissions for browsing-context and location processing.
3. `retrieveBehavioralProfile()` – Retrieve the user's historical behavioral profile.
4. `retrieveMerchantHistory()` – Retrieve historical transactions involving the merchant.
5. `calculateMerchantFamiliarity()` – Determine how familiar the merchant is to the user.
6. `initializeNewMerchantScore()` – Assign a baseline anomaly score of 0.50 to unfamiliar merchants with no transaction history.
7. `applyRecurringMerchantDiscount()` – Reduce the anomaly score by 10% for each qualifying recurring transaction with the same merchant.
8. `analyzeMerchantCategory()` – Compare the transaction category against historical spending patterns.
9. `analyzeTransactionTime()` – Evaluate whether the transaction occurred at an unusual time.
10. `calculateCartSizeAnomaly()` – Calculate transaction amount deviations using Z-score analysis.
11. `retrieveBrowsingContext()` – Request permitted browsing-context data.
12. `matchBrowsingCategories()` – Compare recently viewed categories against the transaction category.
13. `applyBrowsingContextAdjustment()` – Reduce the anomaly score by 0.15 when a qualifying browsing match exists.
14. `retrieveChargebackHistory()` – Retrieve chargeback reports from the previous three months.
15. `applyChargebackAdjustment()` – Increase the anomaly score by 0.10 for each qualifying chargeback.
16. `retrieveNormalSpendingArea()` – Retrieve the user's established geographic spending area.
17. `detectGeographicAnomaly()` – Identify transactions occurring outside normal spending areas.
18. `applyGeographicRiskAdjustment()` – Increase the anomaly score by 0.25 for qualifying geographic anomalies.
19. `retrieveSpendingBudget()` – Retrieve the applicable user spending budget.
20. `detectBudgetViolation()` – Determine whether the transaction exceeds the applicable budget.
21. `applyBudgetRiskAdjustment()` – Increase the anomaly score by 0.10 when the budget is exceeded.
22. `calculateFinalAnomalyScore()` – Combine all applicable risk adjustments and clamp the result between 0 and 1.
23. `classifyTransactionRisk()` – Classify transactions based on the configured risk threshold.
24. `flagSuspiciousTransaction()` – Flag transactions with an anomaly score above 0.85.
25. `triggerTransactionVerification()` – Initiate additional verification for suspicious transactions.
26. `recordFraudAssessment()` – Store the scoring breakdown and assessment outcome.

### Vacation Mode Functions

27. `enableVacationMode()` – Activate vacation tracking.
28. `disableVacationMode()` – Deactivate vacation tracking.
29. `configureVacationDestination()` – Save the user's vacation destination.
30. `configureVacationDates()` – Save the vacation start and end dates.
31. `setVacationBudget()` – Establish the vacation spending budget.
32. `detectVacationTransactions()` – Identify transactions occurring during the vacation period.
33. `associateTransactionWithVacation()` – Associate eligible purchases with the active vacation.
34. `trackVacationMerchantLocation()` – Record merchant geolocation.
35. `calculateVacationExpenses()` – Calculate total vacation expenditures.
36. `calculateRemainingVacationBudget()` – Calculate remaining available vacation funds.
37. `categorizeVacationSpending()` – Group vacation expenses by category.
38. `generateVacationSpendingSummary()` – Generate a summary of vacation expenditures.
39. `generateVacationSpendingMap()` – Display vacation purchases geographically.
40. `adjustVacationGeographicRisk()` – Account for expected spending locations without disabling other fraud checks.

## 4. Proactive Subscription Management

`engine-subscription-mgr`

1. `retrieveTransactionHistory()` – Retrieve historical transaction records.
2. `identifyRecurringTransactions()` – Detect repeated merchant charges.
3. `detectMonthlySubscriptions()` – Identify recurring monthly charges.
4. `detectAnnualSubscriptions()` – Identify recurring annual charges.
5. `verifySubscriptionPattern()` – Validate recurring billing patterns.
6. `registerSubscription()` – Create a subscription record.
7. `updateSubscriptionStatus()` – Update subscription status.
8. `categorizeSubscription()` – Classify subscriptions by service category.
9. `predictNextBillingDate()` – Estimate the next subscription charge.
10. `scheduleBillingNotification()` – Schedule a notification three days before billing.
11. `sendUpcomingBillingAlert()` – Notify the user of an upcoming subscription payment.
12. `detectOverlappingSubscriptions()` – Identify multiple subscriptions in the same category.
13. `detectStreamingRedundancy()` – Identify overlapping streaming subscriptions.
14. `detectCloudStorageRedundancy()` – Identify overlapping cloud storage subscriptions.
15. `calculateFitnessSubscriptionSpending()` – Calculate combined fitness and wellness spending.
16. `detectExcessiveSubscriptionSpending()` – Identify fitness and wellness spending exceeding $150 monthly.
17. `generateSubscriptionRecommendations()` – Suggest opportunities to consolidate subscriptions.
18. `generateSubscriptionUsageAudit()` – Prompt users to review subscription usage.
19. `preventDuplicateNotifications()` – Prevent duplicate billing alerts.
20. `generateSubscriptionSummary()` – Display subscriptions and upcoming charges.

## 5. Inflation Tracking & Real Wage Analysis

`engine-inflation-tracker`

1. `retrieveQuarterlyIncome()` – Retrieve historical quarterly income.
2. `retrieveQuarterlyExpenses()` – Retrieve historical quarterly expenses.
3. `retrieveCPIData()` – Retrieve Consumer Price Index data from Statistics Canada.
4. `normalizeCPIData()` – Normalize CPI values to a consistent reference period.
5. `calculateRealIncome()` – Calculate inflation-adjusted income.
6. `calculateRealExpenses()` – Calculate inflation-adjusted expenses.
7. `calculateRealIncomeGrowth()` – Calculate quarter-over-quarter real income growth.
8. `calculateRealExpenseGrowth()` – Calculate quarter-over-quarter real expense growth.
9. `compareIncomeAndExpenseGrowth()` – Compare real income growth against expense growth.
10. `detectOverspending()` – Identify when real expenses exceed real income under the defined alert conditions.
11. `detectWageStagnation()` – Identify declining real income and purchasing power.
12. `calculatePurchasingPower()` – Estimate changes in the user's purchasing power.
13. `generateInflationAlerts()` – Generate relevant financial alerts.
14. `generateInflationSummary()` – Explain changes in income, expenses, and purchasing power.

## 6. Visual Expense Pyramid

`engine-expense-pyramid`

1. `retrieveMonthlyExpenses()` – Retrieve monthly outgoing transactions.
2. `retrieveMonthlyIncome()` – Retrieve monthly incoming funds.
3. `categorizeEssentialExpenses()` – Identify household bills, loan payments, and insurance.
4. `categorizeNecessaryExpenses()` – Identify groceries, transportation, and basic utilities.
5. `categorizeDiscretionaryExpenses()` – Identify entertainment, withdrawals, and discretionary spending.
6. `mapExpensesToPyramidLevels()` – Assign expenses to Base, Middle, and Peak.
7. `calculateBaseSpendingRatio()` – Calculate essential fixed-cost allocation.
8. `calculateMiddleSpendingRatio()` – Calculate necessary living-cost allocation.
9. `calculatePeakSpendingRatio()` – Calculate discretionary spending allocation.
10. `calculatePyramidDeformity()` – Measure deviation from the 50/30/20 targets.
11. `detectInvertedPyramid()` – Identify when discretionary spending exceeds essential fixed costs.
12. `classifyPyramidHealth()` – Determine the user's spending structure and risk level.
13. `calculateSpendingReallocation()` – Determine potential spending adjustments.
14. `generatePyramidRecommendations()` – Generate personalized spending recommendations.
15. `generatePyramidVisualization()` – Return data for the visual expense pyramid.
16. `generatePyramidSummary()` – Explain the user's spending distribution.

## 7. Generative AI Financial Summaries & Planning

`engine-gemini-integration`

1. `retrievePredictiveInsights()` – Retrieve financial forecasts and runway estimates.
2. `retrieveExpensePyramidInsights()` – Retrieve spending distribution and deformity scores.
3. `retrieveShockMediationInsights()` – Retrieve financial shock and installment information.
4. `retrieveSubscriptionInsights()` – Retrieve recurring expenses and subscription recommendations.
5. `retrieveInflationInsights()` – Retrieve purchasing power and real wage analysis.
6. `retrieveFraudInsights()` – Retrieve relevant transaction risk information.
7. `aggregateFinancialMetrics()` – Consolidate outputs from the financial engines.
8. `buildFinancialSummaryPrompt()` – Construct the Gemini prompt.
9. `analyzeFinancialHealth()` – Generate a personalized financial health assessment.
10. `generateSpendingSummary()` – Explain spending habits and trends.
11. `generateFinancialRecommendations()` – Generate personalized financial recommendations.
12. `generateContingencyPlan()` – Generate financial plans for hypothetical emergencies.
13. `generateShockScenarioAnalysis()` – Explain the potential impact of a financial shock.
14. `validateAIResponse()` – Validate AI-generated statements against verified financial data.
15. `formatFinancialSummary()` – Prepare the response for frontend display.
16. `forwardSummaryToTTS()` – Send finalized text to ElevenLabs.
17. `handleGeminiFailure()` – Handle API failures and provide appropriate fallback behavior.

## 8. Vocal Financial Summaries

`engine-elevenlabs-integration`

1. `receiveFinancialSummary()` – Receive finalized Gemini-generated text.
2. `selectVoiceProfile()` – Select the configured professional or empathetic voice.
3. `configureVoiceParameters()` – Configure voice settings.
4. `generateSpeechAudio()` – Convert financial text into speech.
5. `generateMP3File()` – Generate audio in MP3 format.
6. `streamAudioToClient()` – Stream or securely deliver generated audio.
7. `storeAudioAsset()` – Store audio when required and permitted.
8. `retrieveAudioAsset()` – Retrieve previously generated audio.
9. `handleAudioPlayback()` – Support client-side playback.
10. `handleAudioGenerationFailure()` – Handle failed audio-generation requests.

## 9. Cross-Service & Platform Functions

These functions support the operation of the entire Financial Resilience Engine.

1. `authenticateUser()` – Authenticate users.
2. `authorizeServiceRequest()` – Verify service-level access permissions.
3. `validateRequestPayload()` – Validate incoming API requests.
4. `manageUserConsent()` – Manage browsing-context and geolocation permissions.
5. `publishFinancialEvent()` – Publish events between microservices.
6. `consumeFinancialEvent()` – Process incoming financial events.
7. `scheduleBackgroundJob()` – Schedule recurring background processes.
8. `manageNotificationDelivery()` – Manage push notifications and alerts.
9. `preventDuplicateProcessing()` – Ensure idempotent transaction processing.
10. `recordAuditEvent()` – Maintain audit records.
11. `monitorServiceHealth()` – Monitor microservice availability.
12. `manageAPIErrors()` – Handle API failures and integration errors.
13. `manageExternalAPIConnections()` – Manage third-party API integrations.
14. `encryptSensitiveFinancialData()` – Protect sensitive financial information.
15. `manageDataRetention()` – Apply data retention and deletion policies.
16. `generateSystemMetrics()` – Monitor system performance and operational metrics.

## Total Function Inventory

# 164

Listed functions across the Financial Resilience Engine

| Microservice | Functions |
| --- | --- |
| Shock Mediation | 15 |
| Predictive Planning | 15 |
| Behavioral Fraud | 40 |
| Subscription Management | 20 |
| Inflation Tracking | 14 |
| Expense Pyramid | 16 |
| Gemini Integration | 17 |
| ElevenLabs Integration | 10 |
| Cross-Service Platform | 16 |
| Total | 163 |

Note: The correct total is 163 functions.

These are logical function names and responsibilities, not necessarily 163 separate API endpoints. Some should be implemented as internal methods, shared utilities, background jobs, or service operations.