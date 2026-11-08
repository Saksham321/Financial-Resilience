"""
Judge-Exact Financial Metrics & Runway Engine.
Sheridan Datathon 2026 - Tangerine Track
"""

from typing import Any

from app.engines.calculations import D, money
from app.reference_engines.data_loader import DataLoader


def compute_judge_metrics(account_id: int, data_loader: DataLoader | None = None) -> dict[str, Any]:
    """
    Computes baseline metrics following the exact judge rules from the Datathon README.
    
    Definitions:
    - Typical monthly money in (I): Median of money_in
    - Typical fixed costs (F): Median of household_bills + insurance + loan_payments
    - Typical monthly spending (S): Median of money_out
    - Buffer (B): Mean of avg_daily_balance over the account's last 6 rows, sorted by month
    - Household bills (H): Median of household_bills
    - Loan payment (P): monthly_payment in loans.csv if running at end of 2025, else 0
    """
    dl = data_loader or DataLoader.get_instance()
    ms = dl.get_monthly_summary(account_id)
    
    if ms.empty:
        raise ValueError(f"Account {account_id} has no monthly summary data.")
    
    # Sort by month
    ms_sorted = ms.sort_values(by="month").copy()
    
    # 1. Typical monthly money in (I)
    I = float(ms_sorted["money_in"].median())
    
    # 2. Typical fixed costs (F)
    fixed_series = ms_sorted["household_bills"] + ms_sorted["insurance"] + ms_sorted["loan_payments"]
    F = float(fixed_series.median())
    
    # 3. Typical monthly spending (S)
    S = float(ms_sorted["money_out"].median())
    
    # 4. Buffer (B): Mean of avg_daily_balance over the account's last 6 rows
    last6 = ms_sorted.tail(6)
    B = float(last6["avg_daily_balance"].mean())
    
    # 5. Household bills (H)
    H = float(ms_sorted["household_bills"].median())
    
    # 6. Loan payment (P)
    loan = dl.get_loan(account_id)
    P = 0.0
    if loan and loan.get("is_active_end_2025", False):
        P = float(loan.get("monthly_payment", 0.0))
        
    I,S,F,B,H,P=[float(money(v)) for v in (I,S,F,B,H,P)]

    # Additional helpful metrics
    discretionary = float((
        ms_sorted["card_withdrawals"] + 
        ms_sorted["cash_withdrawals_genuine"] + 
        ms_sorted["transfers_out_other"]
    ).median())
    
    latest_month = str(ms_sorted["month"].iloc[-1])
    latest_balance = float(ms_sorted["month_end_balance"].iloc[-1])
    recent_days_below_zero = int(last6["days_below_zero"].sum())
    
    # Baseline Runway (months)
    baseline_runway, baseline_gap = calculate_runway(buffer=B, spending=S, income=I, one_off_costs=0.0)
    
    # Monthly net cash flow
    net_monthly = float(money(D(str(I))-D(str(S))))
    savings_rate = (net_monthly / I) if I > 0 else 0.0
    
    return {
        "account_id": int(account_id),
        "latest_month": latest_month,
        "latest_balance": round(latest_balance, 2),
        "typical_income_I": round(I, 2),
        "typical_spending_S": round(S, 2),
        "typical_fixed_costs_F": round(F, 2),
        "savings_buffer_B": round(B, 2),
        "household_bills_H": round(H, 2),
        "loan_payment_P": round(P, 2),
        "discretionary_spending": round(discretionary, 2),
        "net_monthly_cashflow": round(net_monthly, 2),
        "savings_rate_pct": round(savings_rate * 100, 1),
        "recent_days_below_zero": recent_days_below_zero,
        "baseline_gap": round(baseline_gap, 2),
        "baseline_runway_months": baseline_runway,
    }


def calculate_runway(
    buffer: float,
    spending: float,
    income: float,
    one_off_costs: float = 0.0
) -> tuple[float | str, float]:
    """
    Runway calculation matching the exact Datathon specification:
    
    buffer_left = float(money(D(str(B))-D(str(one_off_costs))))
    gap         = spending_after_shock - income_after_shock
    if buffer_left <= 0:  runway = 0
    elif gap <= 0:        runway = "no shortfall (120+)"
    else:                 runway = min(buffer_left / gap, 120)
    
    Runway is rounded to 1 decimal.
    """
    buffer_left = float(money(D(str(buffer))-D(str(one_off_costs))))
    gap = float(money(D(str(spending))-D(str(income))))
    
    if buffer_left <= 0:
        return 0.0, gap
    elif gap <= 0:
        return "no shortfall (120+)", gap
    else:
        runway_val = round(min(buffer_left / gap, 120.0), 1)
        return runway_val, gap


def evaluate_shock_scenario(
    account_id: int,
    scenario_id: str = "CUSTOM",
    income_reduction_pct: float = 0.0,
    bills_increase_pct: float = 0.0,
    one_off_costs: float = 0.0,
    shock_duration_months: int = 6,
    custom_label: str | None = None,
    data_loader: DataLoader | None = None
) -> dict[str, Any]:
    """
    Applies preset or custom shock twists and recalculates runway and impact.
    
    Presets:
    - 'LAID_OFF_EI': EI pays 55% of income for 6 months (income = 0.55 * I)
    - 'FURNACE_REPAIR': Surprise repair = 1 full month of typical spending (one_off_costs = S)
    - 'LAID_OFF_AND_BILLS_UP': Laid off (EI at 55%) + bills up 15% (income = 0.55 * I, spending = S + 0.15 * H)
    - 'INFLATION_STAGNATION': Bills up 20%, income reduced 10%
    """
    base = compute_judge_metrics(account_id, data_loader)
    
    I = base["typical_income_I"]
    S = base["typical_spending_S"]
    H = base["household_bills_H"]
    B = base["savings_buffer_B"]
    
    # Process Preset scenarios
    scenario = scenario_id.upper()
    title = custom_label or "Custom Scenario"
    description = ""
    
    if scenario == "LAID_OFF_EI":
        title = "Job Loss with EI (55%)"
        description = "Hypothetical assumption: income falls to 55% for six months. This is not an EI eligibility or benefit determination."
        income_reduction_pct = 0.45  # Remaining 55%
        bills_increase_pct = 0.0
        one_off_costs = 0.0
        shock_duration_months = 6
    elif scenario == "FURNACE_REPAIR":
        title = "Emergency Home/Furnace Repair"
        description = "Surprise repair costing a full month of typical spending."
        income_reduction_pct = 0.0
        bills_increase_pct = 0.0
        one_off_costs = S
        shock_duration_months = 1
    elif scenario == "LAID_OFF_AND_BILLS_UP":
        title = "Job Loss (EI 55%) + Bills Up 15%"
        description = "Hypothetical assumption: income falls to 55% and household bills increase 15%; no benefit eligibility is implied."
        income_reduction_pct = 0.45
        bills_increase_pct = 0.15
        one_off_costs = 0.0
        shock_duration_months = 6
    elif scenario == "INFLATION_STAGNATION":
        title = "Cost of Living Squeeze"
        description = "Household bills up 25% due to utility and rent inflation, real income down 10%."
        income_reduction_pct = 0.10
        bills_increase_pct = 0.25
        one_off_costs = 0.0
        shock_duration_months = 12

    # Calculate post-shock income & spending
    income_shock = float(money(max(D(0),D(str(I))*(D(1)-D(str(income_reduction_pct))))))
    spending_shock = float(money(max(D(0),D(str(S))+D(str(bills_increase_pct))*D(str(H)))))
    buffer_left = float(money(D(str(B))-D(str(one_off_costs))))
    
    runway_shock, gap_shock = calculate_runway(
        buffer=B,
        spending=spending_shock,
        income=income_shock,
        one_off_costs=one_off_costs
    )
    
    # Determine resilience classification
    runway_numeric = runway_shock if isinstance(runway_shock, (int, float)) else 120.0
    if runway_numeric < 2.0:
        resilience_tier = "CRITICAL_RISK"
        tier_description = "The benchmark buffer is exhausted or covers fewer than two months of modeled shortfall. Review essential commitments and near-term cash needs."
    elif runway_numeric < 6.0:
        resilience_tier = "HIGH_VULNERABILITY"
        tier_description = ""
    elif runway_numeric < 12.0:
        resilience_tier = "MODERATE_RESILIENCE"
        tier_description = "The benchmark buffer covers six to twelve months of the modeled shortfall, subject to the stated assumptions."
    else:
        resilience_tier = "STRONG_RESILIENCE"
        tier_description = "The benchmark covers at least twelve months or has no ongoing shortfall. This estimate does not guarantee future resilience."
        
    return {
        "account_id": account_id,
        "scenario_id": scenario,
        "scenario_title": title,
        "scenario_description": description,
        "shock_parameters": {
            "income_reduction_pct": round(income_reduction_pct * 100, 1),
            "bills_increase_pct": round(bills_increase_pct * 100, 1),
            "one_off_costs": round(one_off_costs, 2),
            "shock_duration_months": shock_duration_months,
        },
        "baseline": {
            "income": I,
            "spending": S,
            "buffer": B,
            "runway": base["baseline_runway_months"],
            "net_monthly": base["net_monthly_cashflow"]
        },
        "post_shock": {
            "income": round(income_shock, 2),
            "spending": round(spending_shock, 2),
            "one_off_deducted": round(one_off_costs, 2),
            "buffer_left": round(buffer_left, 2),
            "monthly_gap": round(gap_shock, 2),
            "runway_months": runway_shock,
            "resilience_tier": resilience_tier,
            "tier_description": tier_description
        }
    }
