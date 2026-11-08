"""
Visual Expense Pyramid Engine (engine-expense-pyramid).
Sheridan Datathon 2026 - Tangerine Track
"""

from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from app.reference_engines.config import EXPENSE_PYRAMID_TARGETS
from app.reference_engines.data_loader import DataLoader
from app.reference_engines.metrics import compute_judge_metrics

class ExpensePyramidEngine:
    def __init__(self, data_loader: Optional[DataLoader] = None):
        self.dl = data_loader or DataLoader.get_instance()

    def build_expense_pyramid(self, account_id: int) -> Dict[str, Any]:
        """
        Constructs the Expense Hierarchy of Needs:
        - Base (50% ideal): household_bills, loan_payments, insurance (Required, essential fixed costs)
        - Middle (30% ideal): cash withdrawals genuine, bank fees, essential groceries/transit
        - Peak (20% ideal): card_withdrawals, unknown transfers, non-essential discretionary
        
        Calculates Deformity Score, Inverted Pyramid flag, and proposed rearrangement.
        """
        ms = self.dl.get_monthly_summary(account_id)
        if ms.empty:
            raise ValueError(f"No monthly records for account {account_id}")

        # Recent 6-12 months average breakdown
        recent = ms.sort_values(by="month").tail(12).copy()
        
        # 1. Base Tier: Essential fixed costs
        base_spending = float((
            recent["household_bills"] + 
            recent["insurance"] + 
            recent["loan_payments"]
        ).mean())

        # 2. Middle Tier: Necessary flexible costs (genuine cash withdrawals for groceries/living + bank fees)
        middle_spending = float((
            recent["cash_withdrawals_genuine"] + 
            recent["bank_fees"]
        ).mean())

        # 3. Peak Tier: Unnecessary / discretionary spending (card withdrawals + transfers out other)
        peak_spending = float((
            recent["card_withdrawals"] + 
            recent["transfers_out_other"]
        ).mean())

        total_spending = base_spending + middle_spending + peak_spending
        if total_spending <= 0:
            total_spending = float(recent["money_out"].mean()) or 1.0

        # Calculate actual percentages (0.0 to 1.0)
        base_pct = base_spending / total_spending
        middle_pct = middle_spending / total_spending
        peak_pct = peak_spending / total_spending

        # Ideal targets
        ideal_base = EXPENSE_PYRAMID_TARGETS["base"]       # 0.50
        ideal_middle = EXPENSE_PYRAMID_TARGETS["middle"]   # 0.30
        ideal_peak = EXPENSE_PYRAMID_TARGETS["peak"]       # 0.20

        # Deformity Score = sum of absolute variance from ideal targets
        deformity_score_raw = abs(base_pct - ideal_base) + abs(middle_pct - ideal_middle) + abs(peak_pct - ideal_peak)
        # Scaled to 0 - 100 for intuitive presentation (max variance is ~2.0, so * 50)
        deformity_score = round(min(100.0, deformity_score_raw * 50.0), 1)

        # Inverted Pyramid Flag
        is_inverted = peak_pct > base_pct

        # Visual status classification
        if is_inverted:
            visual_status = "Inverted Pyramid (Critical Risk)"
            status_color = "#dc2626" # Red
        elif deformity_score > 35.0:
            visual_status = "Highly Deformed (Top-Heavy)"
            status_color = "#ea580c" # Orange
        elif deformity_score > 18.0:
            visual_status = "Moderately Deformed"
            status_color = "#d97706" # Amber
        else:
            visual_status = "Healthy / Balanced"
            status_color = "#16a34a" # Green

        # Proposed rearrangement calculation
        rearrangement_cad = 0.0
        if peak_pct > ideal_peak:
            excess_peak_pct = peak_pct - ideal_peak
            rearrangement_cad = round(excess_peak_pct * total_spending, 2)
            proposed_rearrangement = f"Shift ${rearrangement_cad:,.2f}/mo from Peak discretionary spending to Base emergency reserve to restore structural balance."
        else:
            proposed_rearrangement = "Spending structure is well aligned with Tangerine resilience targets. Maintain emergency buffer growth."

        metrics = compute_judge_metrics(account_id, self.dl)

        return {
            "account_id": account_id,
            "visual_status": visual_status,
            "status_color": status_color,
            "deformity_score": deformity_score,
            "is_inverted": is_inverted,
            "total_monthly_spending": round(total_spending, 2),
            "typical_monthly_income": metrics["typical_income_I"],
            "user_pyramid_ratios": {
                "base_pct": round(base_pct * 100, 1),
                "middle_pct": round(middle_pct * 100, 1),
                "peak_pct": round(peak_pct * 100, 1),
            },
            "user_pyramid_amounts": {
                "base_cad": round(base_spending, 2),
                "middle_cad": round(middle_spending, 2),
                "peak_cad": round(peak_spending, 2),
            },
            "ideal_pyramid_ratios": {
                "base_pct": round(ideal_base * 100, 1),
                "middle_pct": round(ideal_middle * 100, 1),
                "peak_pct": round(ideal_peak * 100, 1),
            },
            "proposed_rearrangement": proposed_rearrangement,
            "rearrangement_amount_cad": rearrangement_cad
        }
