"""Compatibility wrapper over the shared daily source-account planning model."""
from app.engines.source_planning import source_plan
from app.reference_engines.data_loader import DataLoader
from app.reference_engines.expense_pyramid import ExpensePyramidEngine
from app.reference_engines.metrics import compute_judge_metrics


class PredictivePlanningEngine:
    def __init__(self,data_loader=None):self.dl=data_loader or DataLoader.get_instance()
    def generate_predictive_plan(self,account_id,window_months=12):
        rows=self.dl.get_monthly_summary(account_id).sort_values('month').tail(window_months).to_dict(orient='records')
        return source_plan(rows,compute_judge_metrics(account_id,self.dl),ExpensePyramidEngine(self.dl).build_expense_pyramid(account_id))
