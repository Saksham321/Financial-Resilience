"""Compatibility wrapper over the shared expense-allocation engine."""
from app.engines.expense_allocation import allocation_from_months
from app.reference_engines.data_loader import DataLoader
from app.reference_engines.metrics import compute_judge_metrics


class ExpensePyramidEngine:
    def __init__(self,data_loader=None):self.dl=data_loader or DataLoader.get_instance()
    def build_expense_pyramid(self,account_id):
        metrics=compute_judge_metrics(account_id,self.dl)
        result=allocation_from_months(self.dl.get_monthly_summary(account_id).to_dict(orient='records'),metrics['typical_income_I'])
        return {**result,'account_id':account_id,'is_inverted':result['inverted'],
            'total_monthly_spending':result['total_spending'],'typical_monthly_income':metrics['typical_income_I'],
            'user_pyramid_ratios':{k+'_pct':v for k,v in result['actual_percent'].items()},
            'user_pyramid_amounts':{k+'_cad':v for k,v in result['totals'].items()},
            'ideal_pyramid_ratios':{k+'_pct':v for k,v in result['target_percent'].items()},
            'rearrangement_amount_cad':result['reallocation_amount']}
