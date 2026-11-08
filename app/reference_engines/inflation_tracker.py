"""
Inflation Tracking & Real Wage Analysis Engine (engine-inflation-tracker).
Sheridan Datathon 2026 - Tangerine Track
"""

from typing import Dict, Any, List, Optional
import pandas as pd
from app.reference_engines.config import CANADIAN_CPI_INDEX
from app.reference_engines.data_loader import DataLoader

class InflationTrackerEngine:
    def __init__(self, data_loader: Optional[DataLoader] = None):
        self.dl = data_loader or DataLoader.get_instance()
        self.cpi = CANADIAN_CPI_INDEX

    def analyze_inflation_impact(self, account_id: int) -> Dict[str, Any]:
        """
        Calculates trailing quarterly nominal vs real income and expenses,
        evaluates QoQ growth rates, and triggers overspending or stagnation alerts.
        """
        ms = self.dl.get_monthly_summary(account_id)
        if ms.empty:
            raise ValueError(f"No monthly records found for account {account_id}")

        ms_sorted = ms.sort_values(by="month").copy()
        
        # Latest CPI reference (2025-12)
        base_cpi_key = "2025-12"
        base_cpi = self.cpi.get(base_cpi_key, 168.6)

        # Aggregate by Quarter (e.g. 2024-Q1, 2024-Q2, 2024-Q3, etc.)
        ms_sorted["quarter"] = ms_sorted["month"].apply(
            lambda m: f"{m[:4]}-Q{(int(m[5:7]) - 1) // 3 + 1}"
        )
        
        # Attach monthly CPI
        ms_sorted["cpi"] = ms_sorted["month"].apply(lambda m: self.cpi.get(m, base_cpi))
        
        # Calculate monthly real values adjusted to end-of-2025 purchasing power
        ms_sorted["real_money_in"] = ms_sorted["money_in"] * (base_cpi / ms_sorted["cpi"])
        ms_sorted["real_money_out"] = ms_sorted["money_out"] * (base_cpi / ms_sorted["cpi"])

        quarterly = ms_sorted.groupby("quarter").agg({
            "money_in": "sum",
            "money_out": "sum",
            "real_money_in": "sum",
            "real_money_out": "sum",
            "cpi": "mean"
        }).reset_index()

        # Focus on trailing 4 to 8 quarters
        trailing_q = quarterly.tail(6).copy()
        q_records = []
        alerts = []

        prev_real_in = None
        prev_real_out = None

        for idx, row in trailing_q.iterrows():
            q_name = row["quarter"]
            nom_in = float(row["money_in"])
            nom_out = float(row["money_out"])
            real_in = float(row["real_money_in"])
            real_out = float(row["real_money_out"])
            avg_cpi = float(row["cpi"])

            real_in_qoq = None
            real_out_qoq = None

            if prev_real_in is not None and prev_real_in > 0:
                real_in_qoq = (real_in - prev_real_in) / prev_real_in
            if prev_real_out is not None and prev_real_out > 0:
                real_out_qoq = (real_out - prev_real_out) / prev_real_out

            q_records.append({
                "quarter": q_name,
                "nominal_money_in": round(nom_in, 2),
                "nominal_money_out": round(nom_out, 2),
                "real_money_in": round(real_in, 2),
                "real_money_out": round(real_out, 2),
                "cpi_index": round(avg_cpi, 1),
                "real_income_qoq_pct": round(real_in_qoq * 100, 2) if real_in_qoq is not None else None,
                "real_expenses_qoq_pct": round(real_out_qoq * 100, 2) if real_out_qoq is not None else None
            })

            prev_real_in = real_in
            prev_real_out = real_out

        # Evaluate alerts on the most recent completed quarter
        if len(q_records) >= 2:
            latest = q_records[-1]
            in_growth = (latest["real_income_qoq_pct"] or 0.0) / 100.0
            out_growth = (latest["real_expenses_qoq_pct"] or 0.0) / 100.0
            latest_real_in = latest["real_money_in"]
            latest_real_out = latest["real_money_out"]

            # Rule 4: Overspending Alert
            if (out_growth > in_growth) and (latest_real_out > latest_real_in):
                alerts.append({
                    "alert_type": "OVERSPENDING_ALERT",
                    "severity": "HIGH",
                    "title": "Inflation Outpacing Earnings (Overspending Risk)",
                    "message": f"Real expenses grew {latest['real_expenses_qoq_pct']}% QoQ while real income grew only {latest['real_income_qoq_pct']}%. Outflow exceeds inflow."
                })

            # Rule 5: Wage Stagnation Alert
            if in_growth < 0:
                alerts.append({
                    "alert_type": "WAGE_STAGNATION_ALERT",
                    "severity": "MEDIUM",
                    "title": "Purchasing Power Erosion (Wage Stagnation)",
                    "message": f"Real income dropped {abs(latest['real_income_qoq_pct'])}% after adjusting for CPI inflation. Effective purchasing power is decreasing."
                })

        # Calculate overall 2-year inflation impact
        first_q = q_records[0]
        last_q = q_records[-1]
        cpi_change_pct = ((last_q["cpi_index"] - first_q["cpi_index"]) / first_q["cpi_index"]) * 100

        return {
            "account_id": account_id,
            "benchmark_cpi_period": base_cpi_key,
            "period_cpi_increase_pct": round(cpi_change_pct, 2),
            "trailing_quarters": q_records,
            "active_alerts": alerts,
            "summary": {
                "latest_quarter": last_q["quarter"],
                "latest_real_net_flow": round(last_q["real_money_in"] - last_q["real_money_out"], 2),
                "purchasing_power_trend": "EROSION" if (last_q["real_income_qoq_pct"] or 0) < 0 else "STABLE/GROWING"
            }
        }
