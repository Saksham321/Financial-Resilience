"""
Predictive & Actionable Planning Engine (engine-predictive-plan).
Sheridan Datathon 2026 - Tangerine Track
"""

from typing import Dict, Any, List, Optional
import datetime
import numpy as np
import pandas as pd
from app.reference_engines.data_loader import DataLoader
from app.reference_engines.metrics import compute_judge_metrics

class PredictivePlanningEngine:
    def __init__(self, data_loader: Optional[DataLoader] = None):
        self.dl = data_loader or DataLoader.get_instance()

    def generate_predictive_plan(
        self,
        account_id: int,
        window_months: int = 12
    ) -> Dict[str, Any]:
        """
        Executes rolling linear regression on outflow transactions,
        projects zero date and 30/60/90 day balance, and synthesizes actionable runway extensions.
        """
        ms = self.dl.get_monthly_summary(account_id)
        if ms.empty:
            raise ValueError(f"No monthly data found for account {account_id}")

        ms_sorted = ms.sort_values(by="month").tail(window_months).copy()
        N = len(ms_sorted)
        if N < 2:
            raise ValueError(f"Need at least 2 months of history for linear regression, found {N}")

        # Linear regression on monthly money_out
        x = np.arange(N, dtype=float)
        y = ms_sorted["money_out"].values.astype(float)
        
        sum_x = np.sum(x)
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        sum_x2 = np.sum(x ** 2)
        
        denom = (N * sum_x2) - (sum_x ** 2)
        if denom == 0:
            slope_m = 0.0
            intercept_b = np.mean(y)
        else:
            slope_m = ((N * sum_xy) - (sum_x * sum_y)) / denom
            intercept_b = (sum_y - (slope_m * sum_x)) / N

        metrics = compute_judge_metrics(account_id, self.dl)
        current_balance = float(ms_sorted["month_end_balance"].iloc[-1])
        typical_income = metrics["typical_income_I"]
        typical_spending = metrics["typical_spending_S"]
        savings_buffer = metrics["savings_buffer_B"]
        baseline_runway_val = metrics["baseline_runway_months"]

        # Runway days
        if isinstance(baseline_runway_val, (int, float)):
            current_runway_days = int(round(baseline_runway_val * 30.4))
        else:
            current_runway_days = 3650  # 10+ years / no shortfall

        # Project outflow and balance at T+30, T+60, T+90 days (1, 2, 3 months ahead)
        projections = []
        projected_zero_date = None
        running_bal = current_balance
        
        # Latest recorded month in dataset
        last_month_str = str(ms_sorted["month"].iloc[-1]) # e.g. "2025-12"
        last_year, last_m = map(int, last_month_str.split("-"))
        curr_date = datetime.date(last_year, last_m, 28)

        # Discretionary spending baseline
        disc_spending = metrics["discretionary_spending"]
        essential_spending = max(0.0, typical_spending - disc_spending)

        for step in range(1, 13): # simulate up to 12 months ahead
            projected_x = (N - 1) + step
            projected_outflow = max(0.0, float(slope_m * projected_x + intercept_b))
            net_flow = typical_income - projected_outflow
            running_bal += net_flow
            
            future_date = curr_date + datetime.timedelta(days=int(step * 30.4))
            
            if step in [1, 2, 3]:
                projections.append({
                    "horizon_days": step * 30,
                    "target_date": future_date.strftime("%Y-%m-%d"),
                    "projected_monthly_outflow": round(projected_outflow, 2),
                    "projected_balance": round(running_bal, 2)
                })

            if running_bal <= 0 and projected_zero_date is None:
                projected_zero_date = future_date.strftime("%Y-%m-%d")

        # Action Generation Engine: Threshold optimization
        # Suggest 10% and 20% discretionary cuts and calculate exact runway extension
        action_plans = []
        
        if disc_spending > 50.0:
            for pct, act_id in [(0.10, "act_rec_001"), (0.20, "act_rec_002")]:
                cut_amt = disc_spending * pct
                new_spending = typical_spending - cut_amt
                new_gap = new_spending - typical_income
                
                if new_gap <= 0:
                    ext_days = 90
                    ext_desc = "eliminates monthly shortfall completely!"
                elif baseline_runway_val != "no shortfall (120+)":
                    new_runway = min(savings_buffer / new_gap, 120.0)
                    ext_months = max(0.0, new_runway - float(baseline_runway_val))
                    ext_days = int(round(ext_months * 30.4))
                    ext_desc = f"extends runway by ~{round(ext_months, 1)} months ({ext_days} days)"
                else:
                    ext_days = 60
                    ext_desc = "fortifies reserve buffer"

                action_plans.append({
                    "action_id": act_id,
                    "category": "DISCRETIONARY_SPENDING",
                    "target_reduction_pct": pct,
                    "monthly_savings_cad": round(cut_amt, 2),
                    "projected_runway_extension_days": ext_days,
                    "message": f"Reduce discretionary spending by {int(pct*100)}% (${round(cut_amt, 2)}/mo) to {ext_desc}."
                })

        # Add fixed bills review if fixed costs are high
        if metrics["typical_fixed_costs_F"] > typical_income * 0.5:
            action_plans.append({
                "action_id": "act_rec_003",
                "category": "FIXED_COSTS_CONSOLIDATION",
                "target_reduction_pct": 0.05,
                "monthly_savings_cad": round(metrics["typical_fixed_costs_F"] * 0.05, 2),
                "projected_runway_extension_days": 45,
                "message": f"Audit household bills and insurance to target a 5% optimization (${round(metrics['typical_fixed_costs_F']*0.05, 2)}/mo)."
            })

        return {
            "user_id": f"acc_{account_id}",
            "account_id": account_id,
            "forecast": {
                "projected_zero_date": projected_zero_date or "No zero date (buffer positive)",
                "current_runway_days": current_runway_days,
                "trend_slope": round(float(slope_m), 2),
                "trend_direction": "INCREASING_SPEND" if slope_m > 0 else "DECREASING_SPEND",
                "linear_equation": f"y = {round(float(slope_m), 2)}x + {round(float(intercept_b), 2)}",
                "projections_30_60_90": projections
            },
            "spending_breakdown": {
                "essential_monthly": round(essential_spending, 2),
                "discretionary_monthly": round(disc_spending, 2),
                "discretionary_ratio_pct": round((disc_spending / typical_spending * 100), 1) if typical_spending > 0 else 0.0
            },
            "action_plan": action_plans
        }
