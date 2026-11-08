"""
Shock Mediation & Revenue Generation Engine (engine-shock-mediation).
Sheridan Datathon 2026 - Tangerine Track
"""

from typing import Any

from app.engines.calculations import D, installment, money
from app.reference_engines.config import INSTALLMENT_PLANS
from app.reference_engines.data_loader import DataLoader
from app.reference_engines.metrics import compute_judge_metrics


class ShockMediationEngine:
    def __init__(self, data_loader: DataLoader | None = None):
        self.dl = data_loader or DataLoader.get_instance()

    def evaluate_credit_eligibility(self, account_id: int) -> dict[str, Any]:
        """
        Evaluates user's credit eligibility based on historical loans,
        days below zero, and recent account balance trajectory.
        """
        loan = self.dl.get_loan(account_id)
        ms = self.dl.get_monthly_summary(account_id)
        
        # Check loan status
        in_debt = False
        has_defaulted = False
        if loan:
            status = loan.get("status", "")
            if status == "D":
                in_debt = True
            elif status == "B" or loan.get("defaulted") == 1:
                has_defaulted = True
                
        # Check overdraft history (last 6 months days_below_zero)
        last6 = ms.tail(6) if not ms.empty else ms
        recent_days_below_zero = int(last6["days_below_zero"].sum()) if not last6.empty else 0
        avg_buffer = float(last6["avg_daily_balance"].mean()) if not last6.empty else 0.0

        # Eligibility criteria:
        # Cannot be currently in debt (status D), cannot have defaulted (status B),
        # cannot have chronic overdraft (> 15 days below zero in last 6 months),
        # and buffer cannot be deep negative.
        eligible = True
        reasons = []

        if in_debt:
            eligible = False
            reasons.append("Active loan currently in distress/debt (Status D).")
        if has_defaulted:
            eligible = False
            reasons.append("Prior loan default recorded in credit history (Status B).")
        if recent_days_below_zero > 15:
            eligible = False
            reasons.append(f"Excessive overdraft activity: {recent_days_below_zero} days below zero in past 6 months.")
        if avg_buffer < -500.0:
            eligible = False
            reasons.append("Negative cash reserve buffer.")

        risk_tier = "LOW"
        if not eligible:
            risk_tier = "HIGH"
        elif recent_days_below_zero > 0 or loan is not None:
            risk_tier = "MEDIUM"

        return {
            "credit_eligible": eligible,
            "risk_tier": risk_tier,
            "disqualification_reasons": reasons,
            "recent_days_below_zero": recent_days_below_zero,
            "has_active_debt": in_debt,
            "has_default_history": has_defaulted,
            "current_liquid_buffer": round(avg_buffer, 2)
        }

    def calculate_installment_options(self, shortfall: float, risk_tier: str = "HIGH") -> list[dict[str, Any]]:
        """
        Generates structured 3, 6, and 12-month lifeline installment options.
        Protects the consumer from predatory lenders while securing structured revenue for Tangerine.
        """
        plans=[]
        for config in INSTALLMENT_PLANS:
            fee=D(str(config.get('fee_amount',0)))
            terms=installment(D(str(shortfall)),fee,D(str(config['apr'])),config['term_months'])
            plans.append({'term_months':config['term_months'],'principal':terms['principal'],
                'monthly_installment':terms['payment'],'final_installment':terms['schedule'][-1]['payment'],
                'total_repayable':terms['total_repayment'],'projected_bank_revenue':money(terms['total_repayment']-terms['principal']),
                'fee_structure':{'type':config['fee_type'],'amount':fee,'rate':D(str(config['apr']))/100},
                'annual_interest_rate_percent':D(str(config['apr'])),'apr':terms['apr_percent'],
                'apr_method':terms['apr_method'],'schedule':terms['schedule'],
                'description':str(config['term_months'])+'-month hypothetical installment example'})

        return plans

    def mediate_shock(
        self,
        account_id: int,
        shock_amount: float,
        shock_type: str = "EMERGENCY_EXPENSE"
    ) -> dict[str, Any]:
        """
        Core mediation logic:
        1. Query Core Banking -> Fetch liquid_buffer
        2. Calculate Shortfall = shock_amount - liquid_buffer
        3. IF shortfall > 0:
              IF credit_eligible == False:
                 Suggest Lifeline Installment Plans
              ELSE:
                 Route to standard Line of Credit / Overdraft Protection
           ELSE:
              Buffer sufficient; no emergency intervention required.
        """
        metrics = compute_judge_metrics(account_id, self.dl)
        buffer = metrics["latest_balance"]
        income = metrics["typical_income_I"]
        shortfall = max(0.0, shock_amount - buffer)
        
        eligibility = self.evaluate_credit_eligibility(account_id)
        is_eligible = eligibility["credit_eligible"]
        risk_tier = eligibility["risk_tier"]

        if shortfall <= 0:
            return {
                "account_id": account_id,
                "status": "BUFFER_SUFFICIENT",
                "message": "Liquid cash reserves are sufficient to absorb this shock without borrowing.",
                "shock_amount": round(shock_amount, 2),
                "liquid_buffer": round(buffer, 2),
                "shortfall_amount": 0.0,
                "buffer_remaining": round(buffer - shock_amount, 2),
                "credit_evaluation": eligibility,
                "proposal": None
            }

        # Shortfall detected!
        if not is_eligible:
            # High-risk / Ineligible for standard unsecured credit -> Lifeline Installments
            installment_plans = self.calculate_installment_options(shortfall, risk_tier)
            return {
                "account_id": account_id,
                "status": "SHORTFALL_DETECTED",
                "message": "Modeled shortfall detected. Historical risk signals restrict the example credit route. Installments below are hypothetical comparisons.",
                "shock_amount": round(shock_amount, 2),
                "shock_type": shock_type,
                "liquid_buffer": round(buffer, 2),
                "shortfall_amount": round(shortfall, 2),
                "credit_evaluation": eligibility,
                "installment_proposal": {
                    "eligible": True,
                    "action_required": "SELECT_LIFELINE_PLAN",
                    "rationale": "Prevents catastrophic default and overdraft penalties via structured payments.",
                    "plans": installment_plans
                }
            }
        else:
            # Low / Medium risk -> Standard Line of Credit or Overdraft Protection
            credit_limit = round(min(15000.0, max(shortfall * 1.5, income * 1.5)), 2)
            loc_apr = 7.20
            monthly_min_payment = float(money(D(str(min(shortfall,credit_limit)))*D(".03")))
            
            return {
                "account_id": account_id,
                "status": "SHORTFALL_DETECTED",
                "message": "Modeled shortfall detected. Compare an illustrative credit route; no approval or product availability is established.",
                "shock_amount": round(shock_amount, 2),
                "shock_type": shock_type,
                "liquid_buffer": round(buffer, 2),
                "shortfall_amount": round(shortfall, 2),
                "credit_evaluation": eligibility,
                "line_of_credit_proposal": {
                    "eligible": shortfall<=credit_limit,
                    "approved_limit": credit_limit,"modeled_limit":credit_limit,"approved":False,
                    "apr": loc_apr,
                    "estimated_initial_draw": round(min(shortfall,credit_limit),2),"uncovered_shortfall":round(max(0,shortfall-credit_limit),2),
                    "min_monthly_payment": monthly_min_payment,
                    "revolving_access": True,
                    "action_required": "ACCEPT_LINE_OF_CREDIT"
                }
            }
