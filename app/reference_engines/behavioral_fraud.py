"""
Behavioral Fraud Risk Engine (engine-behavioral-fraud).
Sheridan Datathon 2026 - Tangerine Track
"""

from typing import Any

import numpy as np
import pandas as pd

from app.reference_engines.config import FRAUD_CONFIG
from app.reference_engines.data_loader import DataLoader


class BehavioralFraudEngine:
    def __init__(self, data_loader: DataLoader | None = None):
        self.dl = data_loader or DataLoader.get_instance()

    def get_user_baseline(self, account_id: int) -> dict[str, Any]:
        """
        Builds the 90-day baseline profile:
        - Mean and standard deviation of transaction amounts
        - Known merchants and recurring frequencies
        - Frequent categories
        """
        tx = self.dl.get_account_transactions(account_id)
        
        if tx.empty:
            return {
                "mean_cart": None,
                "std_cart": None,
                "known_merchants": {},
                "known_operations": set(),
                "chargebacks_last_3m": 0
            }

        # Historical 90-day window anchored to the last recorded transaction.
        reference=pd.to_datetime(tx['date']).max()
        tx_recent=tx[pd.to_datetime(tx['date'])>=reference-pd.Timedelta(days=89)].copy()
        amounts = tx_recent["amount"].values.astype(float)
        
        mean_cart = float(np.mean(amounts)) if len(amounts) > 0 else None
        std_cart = float(np.std(amounts)) if len(amounts) > 1 else None

        # Known partner banks / merchants
        merchant_counts = {}
        for pb in tx["partner_bank"].dropna():
            pb_str = str(pb).strip()
            merchant_counts[pb_str] = merchant_counts.get(pb_str, 0) + 1

        # Check penalty bank fees / chargebacks
        chargebacks = 0
        if "purpose" in tx_recent.columns:
            cb_mask = tx_recent["purpose"].str.contains("penalty|negative balance", case=False, na=False)
            chargebacks = int(cb_mask.sum())

        return {
            "mean_cart": mean_cart,
            "std_cart": std_cart,
            "known_merchants": merchant_counts,
            "known_operations": set(tx["operation"].dropna().unique()),
            "chargebacks_last_3m": chargebacks
        }

    def evaluate_transaction(
        self,
        account_id: int,
        amount: float,
        merchant_name: str,
        category: str = "RETAIL",
        is_new_store: bool = False,
        recent_browsing_category: str | None = None,
        is_outside_normal_location: bool = False,
        is_outside_budget: bool = False,
        vacation_mode: bool = False,
        vacation_location: str | None = None,
        chargebacks_count: int | None = None
    ) -> dict[str, Any]:
        """
        Executes the behavioral anomaly scoring pipeline according to Section 3 specs:
        1. Base score: 0.50 for all new stores with no transactions.
        2. Recurring merchant: decrease score by 10% for each recurring transaction.
        3. Cart Size Anomaly: Z = (x - mean) / std. Flag if Z > 3.0.
        4. Browsing context: if viewed category recently, reduce by 0.15.
        5. Chargebacks: each chargeback in last 3 months add 0.10.
        6. Location: if outside normal area add 0.25 (waived if vacation_mode is active).
        7. Budget: if outside spending budget add 0.10.
        8. Decision: Flag if score > 0.85.
        """
        baseline = self.get_user_baseline(account_id)
        scoring_breakdown = []

        # 1. Base Score calculation
        known_merchants = baseline["known_merchants"]
        recurring_count = known_merchants.get(merchant_name.strip(), 0)
        
        if is_new_store or recurring_count == 0:
            anomaly_score = FRAUD_CONFIG["new_store_baseline"]
            scoring_breakdown.append({
                "factor": "NEW_STORE_BASELINE",
                "delta": round(FRAUD_CONFIG["new_store_baseline"], 2),
                "detail": f"Merchant '{merchant_name}' has no prior transactions. Baseline set to 0.50."
            })
        else:
            anomaly_score = 0.15
            scoring_breakdown.append({
                "factor": "RECOGNIZED_STORE_BASELINE",
                "delta": 0.15,
                "detail": f"Known merchant '{merchant_name}' ({recurring_count} previous transactions)."
            })
            
            # Recurring merchant discount: decrease by 10% per recurring visit
            discount_factor = (1.0 - FRAUD_CONFIG["recurring_discount_rate"]) ** min(recurring_count, 5)
            discounted_score = anomaly_score * discount_factor
            score_reduction = anomaly_score - discounted_score
            anomaly_score = discounted_score
            scoring_breakdown.append({
                "factor": "RECURRING_MERCHANT_DISCOUNT",
                "delta": -round(score_reduction, 3),
                "detail": f"Trust discount of 10% applied across {min(recurring_count, 5)} visits."
            })

        # 2. Cart Size Z-Score
        mu = baseline["mean_cart"]
        sigma = baseline["std_cart"]
        z_score = (amount-mu)/sigma if mu is not None and sigma is not None and sigma>0 else None
        
        if z_score is not None and z_score > FRAUD_CONFIG["cart_z_threshold"]:
            anomaly_score += FRAUD_CONFIG["cart_z_anomaly_penalty"]
            scoring_breakdown.append({
                "factor": "CART_MAGNITUDE_Z_SCORE",
                "delta": +FRAUD_CONFIG["cart_z_anomaly_penalty"],
                "detail": f"Cart size ${amount:.2f} is an extreme outlier (Z-Score = {z_score:.2f} > 3.0, mean=${mu:.2f}, σ=${sigma:.2f})."
            })
        elif z_score is not None and z_score > 1.5:
            mod_penalty = 0.10
            anomaly_score += mod_penalty
            scoring_breakdown.append({
                "factor": "ELEVATED_CART_SIZE",
                "delta": +mod_penalty,
                "detail": f"Cart size higher than typical (Z-Score = {z_score:.2f})."
            })

        if z_score is None:
            unusual=mu is not None and sigma==0 and amount>3*mu
            if unusual:anomaly_score+=FRAUD_CONFIG['cart_z_anomaly_penalty']
            scoring_breakdown.append({'factor':'CART_MAGNITUDE_Z_SCORE' if unusual else 'INSUFFICIENT_AMOUNT_VARIATION',
                'delta':FRAUD_CONFIG['cart_z_anomaly_penalty'] if unusual else 0,
                'detail':'A statistical Z-score is unavailable. The hypothetical amount exceeds three times the constant recorded amount.' if unusual else 'Insufficient history or amount variation for a statistical Z-score; no substitute baseline is invented.'})

        # 3. Browsing Context Match
        if recent_browsing_category and recent_browsing_category.lower() == category.lower():
            disc = FRAUD_CONFIG["browsing_context_discount"]
            anomaly_score = max(0.0, anomaly_score - disc)
            scoring_breakdown.append({
                "factor": "BROWSING_INTENT_CONFIRMED",
                "delta": -disc,
                "detail": f"Client recently browsed category '{category}'. Reduced risk by 0.15."
            })

        # 4. Chargeback History
        effective_cb = chargebacks_count if chargebacks_count is not None else baseline["chargebacks_last_3m"]
        if effective_cb > 0:
            cb_penalty = effective_cb * FRAUD_CONFIG["chargeback_penalty_each"]
            anomaly_score += cb_penalty
            scoring_breakdown.append({
                "factor": "RECENT_CHARGEBACK_HISTORY",
                "delta": +round(cb_penalty, 2),
                "detail": f"{effective_cb} chargebacks in last 3 months (+{cb_penalty:.2f})."
            })

        # 5. Geolocation & Vacation Mode
        if is_outside_normal_location:
            if vacation_mode:
                scoring_breakdown.append({
                    "factor": "VACATION_MODE_AUTHORIZED",
                    "delta": 0.0,
                    "detail": f"Location anomaly waived due to active Vacation Mode in {vacation_location or 'Travel Destination'}."
                })
            else:
                loc_pen = FRAUD_CONFIG["location_distance_penalty"]
                anomaly_score += loc_pen
                scoring_breakdown.append({
                    "factor": "OUTSIDE_NORMAL_SPENDING_AREA",
                    "delta": +loc_pen,
                    "detail": "Transaction initiated outside customer's primary geographic spending boundary."
                })

        # 6. Outside Spending Budget
        if is_outside_budget:
            budget_pen = FRAUD_CONFIG["budget_exceeded_penalty"]
            anomaly_score += budget_pen
            scoring_breakdown.append({
                "factor": "CATEGORY_BUDGET_EXCEEDED",
                "delta": +budget_pen,
                "detail": f"Amount exceeds allocated monthly budget for {category}."
            })

        # Clamp final score between 0.0 and 1.0
        final_score = max(0.0, min(1.0, anomaly_score))
        threshold = FRAUD_CONFIG["flag_threshold"]
        is_flagged = final_score > threshold

        return {
            "account_id": account_id,
            "merchant_name": merchant_name,
            "category": category,
            "amount": round(amount, 2),
            "anomaly_score": round(final_score, 3),
            "flag_threshold": threshold,
            "decision": "FLAG_HIGH_RISK" if is_flagged else "BELOW_REVIEW_THRESHOLD",
            "is_flagged": is_flagged,
            "vacation_mode_active": vacation_mode,
            "metrics": {
                "z_score": round(z_score, 2) if z_score is not None else None,
                "baseline_mean_cart": round(mu, 2) if mu is not None else None,
                "baseline_std_cart": round(sigma, 2) if sigma is not None else None,
                "recurring_orders_count": recurring_count
            },
            "scoring_breakdown": scoring_breakdown
        }
