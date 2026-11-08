Financial Resilience Engine
System Architecture & Technical Specifications
This document outlines the functional and technical requirements for the Financial Resilience Engine microservices. Designed for developer implementation.


1. Shock Mediation & Revenue Generation (engine-shock-mediation)
1.1 Overview
Evaluates user liquidity against incoming or projected financial shocks. If the shock exceeds available liquid buffers and standard line of credit options are restricted, the service automatically suggests a custom installment plan. This proactive suggestion serves as a critical lifeline to prevent the consumer from going underwater financially, while simultaneously generating structured revenue (via interest or flat fees) for the bank.
1.2 Core Data Requirements & Inputs
Field Name
Type
Source
Description
user_id
 UUID
Auth Context
Unique identifier for the user
shock_amount
Decimal
Event / API Payload
Value of the incoming/detected shock
liquid_buffer
Decimal
Core Banking API
Sum of checking, savings, and immediate cash reserve
credit_eligible
 Boolean
Underwriting Service
Flag indicating if user can access standard lines of credit

1.3 Algorithm & Execution Logic

1. Receive shock payload for user_id.
2. Query Core Banking API -> Fetch liquid_buffer.
3. Calculate Shortfall: 
   shortfall = shock_amount - liquid_buffer
4. IF shortfall > 0:
      IF credit_eligible == FALSE:
         a. Execute Installment Engine (shock_amount, user_risk_tier).
         b. Calculate monthly payment options (3m, 6m, 12m) to keep monthly cash flow positive and prevent the account from going underwater.
         c. Generate payload for Push Notification / Offer UI suggesting the lifeline installment plan.
      ELSE:
         a. Route to standard Line of Credit / Overdraft Protection flow.
   ELSE:
      a. Log buffer sufficient; no intervention required.
1.4 API Contract: Proposed Installment Plan
POST /api/v1/shocks/mediateRequest Payload:

{
  "user_id": "usr_99x821a0004",
  "shock_amount": 1500.00,
  "shock_type": "EMERGENCY_EXPENSE"
}

Response (200 OK):

{
  "status": "SHORTFALL_DETECTED",
  "shortfall_amount": 750.00,
  "installment_proposal": {
    "eligible": true,
    "plans": [
      {
        "term_months": 3,
        "monthly_installment": 260.00,
        "fee_structure": { "type": "FLAT_FEE", "amount": 30.00 },
        "apr": 0.00
      },
      {
        "term_months": 6,
        "monthly_installment": 135.50,
        "fee_structure": { "type": "INTEREST", "rate": 0.085 },
        "apr": 8.50
      }
    ]
  }
}


2. Predictive & Actionable Planning (engine-predictive-plan)
2.1 Overview
Analyzes transaction history to categorize spending, projects cash flow using linear regression over a rolling window, and yields actionable steps to extend financial runway.
2.2 Technical Specs & Linear Regression Model
Historical Window: $N = 6$ to $12$ months of money_out transactions.
Interval Aggregation: Monthly totals ($t_1, t_2, \dots, t_n$).
Trend Calculation: Simple Linear Regression $y = mx + b$ where $x$ represents the month index and $y$ represents total outflow.

$$\text{Slope } (m) = \frac{N \sum(xy) - \sum x \sum y}{N \sum(x^2) - (\sum x)^2}$$
2.3 System Output Matrix
Feature
Logic / Model
Output Target
Categorization
Machine Learning Tagging Pipeline
Grouped monthly totals (Essential vs. Discretionary)
Projection
Linear Trend Model ($y = mx + b$)
Estimated Balance at $T + 30, 60, 90$ Days
Action Generation
Rule-Based Threshold Engine
Contextual recommendation string + parametric impact

2.4 Data Output Schema
{
  "user_id": "usr_99x821a0004",
  "forecast": {
    "projected_zero_date": "2024-11-15",
    "current_runway_days": 42,
    "trend_slope": 12.45
  },
  "action_plan": [
    {
      "action_id": "act_rec_001",
      "category": "DISCRETIONARY_SPENDING",
      "target_reduction_pct": 0.10,
      "projected_runway_extension_days": 60,
      "message": "Reduce discretionary spending by 10% to extend your runway by 2 months."
    }
  ]
}


3. Behavioral Fraud Risk Engine (engine-behavioral-fraud)
3.1 Overview
Ingests pending transactions and cross-references them against established behavioral baselines (time of day, merchant category, cart magnitude) and optional client-side browsing context to flag high-risk anomalies.
3.2 Evaluation Pipeline
[ Incoming Transaction Event ]
              │
              ▼
    [ Permissions Check ] ──(Opted In)──► [ Attach Browsing Context Data ]
              │
        (Not Opted In)
              │
              ▼
  [ Fetch Historical Baseline Profile ]
   - Category distribution (last 90d)
   - Geo / Time-of-day matrices
   - Cart size standard deviation (σ)
              │
              ▼
  [ Score Anomaly (0.0 - 1.0) ]
              │
   ┌──────────┴──────────┐
   ▼                     ▼
[ Score > 0.85 ]      [ Score <= 0.85 ]
   │                     │
   ▼                     ▼
[ Flag Transaction ]  [ Pass / Approve ]
3.3 Risk Scoring Vector Specifications
Merchant Category Match: Binary/Weighted frequency check against user's top-tier categories.
Cart Size Anomaly: Z-Score calculation $Z = \frac{x - \mu}{\sigma}$. Flags if $Z > 3.0$.
Browsing Context Match: String similarity score (e.g., Jaro-Winkler) between browsing session tags and merchant metadata.


eeee
All new stores with no transactions will have a score of (0.5 for example)
Decrease the anomaly score by 10% for each recurring transaction with the same merchant

Call the API to analyze browsing data if transaction is in a category that they have viewed recently reduce (by 0.15)


Check database for charge back reports (each charge back in the last 3 months add 0.1)
If location is further by normal spending area defined by nearby merchant details or user setup choice (add 0.25) 
If outside of spending budget (add 0.1) 


Also add a vacation mode to track expense spent on a vacation and also track the geolocation of such stores

4. Proactive Subscription Management (engine-subscription-mgr)
4.1 Overview
Identifies recurring subscription billing patterns, schedules proactive user 7777notifications prior to charges, and detects overlapping service redundancies.
4.2 Pattern Detection & Notification Logic
Recurring Identification: Scan transactions table for identical merchant descriptions occurring at $28\text{--}31$ day intervals (or annual equivalents).
Alert Trigger: Set a scheduled job to issue a push event at $T - 3\text{ days}$ relative to the predicted next billing date.
4.3 Overlap Analysis Matrix
Identified Category
Detected Services (Example)
Action Trigger Condition
System Output
STREAMING_VIDEO
Platform A, Platform B, Platform C
 Active subscriptions $\ge 2$ in same category
 Prompt consolidation alert
CLOUD_STORAGE
Service X, Service Y
 Active subscriptions $\ge 2$ in same category
 Prompt consolidation alert
FITNESS_WELLNESS
Gym Pass, App Subscription
 Category spend $> $150/\text{mo}$ combined
 Prompt usage audit prompt

4.4 Data Model: Subscription State
{
  "subscription_id": "sub_883a12",
  "user_id": "usr_99x821a0004",
  "merchant_name": "StreamCo Premium",
  "category": "STREAMING_VIDEO",
  "amount": 14.99,
  "cadence": "MONTHLY",
  "next_billing_date": "2024-10-28",
  "notification_scheduled_for": "2024-10-25",
  "overlap_detected": true,
  "overlapping_subscription_ids": ["sub_994b11", "sub_102c44"]
}


5. Inflation Tracking & Real Wage Analysis (engine-inflation-tracker)
5.1 Overview
Tracks user purchasing power over time by adjusting income and expenses against the Consumer Price Index (CPI), alerting users if their real wages are stagnating or if they are overspending relative to inflation.
5.2 Core Data Requirements & Inputs
Field Name
Type
Source
Description
user_id
 UUID
Auth Context
Unique identifier for the user
money_in_quarterly
 Decimal(12,2)
Aggregated Transactions
User's total income per quarter
money_out_quarterly
 Decimal(12,2)
Aggregated Transactions
User's total expenses per quarter
cpi_index
 Decimal(12,2)
StatCan API
Monthly Consumer Price Index

5.3 Execution Logic
1. Fetch trailing 4 quarters of money_in and money_out.
2. Adjust historical totals using cpi_index to calculate 'Real Income' and 'Real Expenses'.
3. Calculate Quarter-over-Quarter (QoQ) growth rates.
4. IF (Real_Expenses_QoQ > Real_Income_QoQ) AND (Real_Expenses > Real_Income):
      Trigger Overspending Alert.
5. IF (Real_Income_QoQ < 0):
      Trigger Wage Stagnation Alert (purchasing power is dropping).


6. Visual Expense Pyramid (engine-expense-pyramid)
6.1 Overview
Categorizes expenses into a hierarchy of needs (Essential at the bottom, Discretionary at the top). Calculates how 'deformed' the user's spending pyramid is compared to a healthy baseline and provides actionable steps to rearrange spending.
6.2 Categorization Matrix
Pyramid Level
Included Categories
Ideal Target %
Description
Base (Bottom)
household_bills, loan_payments, insurance
50%
Required, essential fixed costs.
Middle
Groceries, transit, basic utilities
30%
Flexible but necessary living costs.
Peak (Top)
card_withdrawals, entertainment, unknown transfers
20%
Unnecessary / discretionary spending.

6.3 Deformity Calculation & Output
1. Map user's monthly money_out to Base, Middle, and Peak tiers.
2. Calculate Actual % for each tier relative to total money_in.
3. Compute 'Deformity Score' = Sum of absolute variance from Ideal Targets.
4. IF Peak % > Base %:
      Flag as "Inverted Pyramid" (Critical Risk).
5. Generate UI payload:
   - user_pyramid_ratios: { base: 25, middle: 25, peak: 50 }
   - visual_status: "Highly Deformed (Top-Heavy)"
   - proposed_rearrangement: "Shift $X from Peak to Base/Savings to stabilize."


7. Generative AI Summaries & Planning (engine-gemini-integration)
7.1 Overview
Utilizes the Gemini API to analyze quantitative financial data and generate highly personalized, concise, and conversational text summaries of spending habits, financial health, and contingency plans.
7.2 Core Data Requirements & Inputs
Field Name
Type
Source
Description
user_id
 UUID
Auth Context
Unique identifier for the user
financial_metrics
JSON
Engine Output
Aggregated metrics (runway, spending trends, pyramid deformity)
shock_scenario
JSON
Event Payload
Details of the selected shock (e.g., job loss, emergency expense)

7.3 Execution Logic
1. Aggregate output from predictive-plan, expense-pyramid, and shock-mediation engines.
2. Construct prompt template injecting financial_metrics and shock_scenario.
3. Call Gemini API to generate concise spending summary and personalized action plan.
4. Return AI-generated text payload to the UI layer and pass to ElevenLabs TTS service.

8. Vocal Financial Summaries (engine-elevenlabs-integration)
8.1 Overview
Leverages the ElevenLabs TTS (Text-to-Speech) API to convert the Gemini-generated financial summaries and plans into empathetic, human-like audio insights, enhancing accessibility and user engagement.
8.2 Execution Logic
1. Receive finalized text string from the Gemini integration service.
2. Select appropriate ElevenLabs voice ID (e.g., empathetic, professional tone).
3. Call ElevenLabs TTS API with the text payload.
4. Stream the generated audio file (.mp3) to the client application for playback.

