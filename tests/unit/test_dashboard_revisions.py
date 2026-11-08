from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace
import pandas as pd
import pytest
from app.engines.expense_allocation import build_allocation,threshold_state,allocation_from_months
from app.engines.source_planning import source_forecast,source_plan
from app.engines.calculations import installment
from app.reference_engines.service import briefing
from app.reference_engines.metrics import evaluate_shock_scenario,calculate_runway
from app.reference_engines.recorded_subscriptions import recorded_commitments
from app.reference_engines.inflation_tracker import InflationTrackerEngine
from app.reference_engines.behavioral_fraud import BehavioralFraudEngine


def rows(income=1000,spending=900,balance=1300):
    return [dict(month=f'2025-{n:02}',money_in=income,money_out=spending,month_end_balance=balance,
        avg_daily_balance=1200,household_bills=100,insurance=50,loan_payments=100,bank_fees=10,
        cash_withdrawals_genuine=400,card_withdrawals=200,transfers_out_other=40,days_below_zero=0) for n in range(1,13)]

class Loader:
    def __init__(self,monthly=None):self.monthly=pd.DataFrame(monthly if monthly is not None else rows())
    def get_monthly_summary(self,_):return self.monthly.copy()
    def get_loan(self,_):return None
    def get_account_transactions(self,_):return pd.DataFrame()

@pytest.mark.parametrize('value,target,expected',[(14.99,20,'below'),(15,20,'near'),(20,20,'near'),(20.01,20,'over'),(45,50,'near'),(24,30,'below'),(None,20,'unknown')])
def test_shared_allocation_threshold(value,target,expected):assert threshold_state(value,target)==expected


def test_normalized_score_denominator_and_unknowns():
    aligned=build_allocation({'rent':500,'groceries':300,'entertainment':200},income=500)
    assert aligned['deformity_score']==0 and aligned['actual_percent']['base']==50
    assert aligned['income_allocation_percent']['base']==100
    extreme=build_allocation({'entertainment':100})
    assert extreme['deformity_score']==80
    unknown=build_allocation({'cash':100})
    assert unknown['unclassified_total']==100 and unknown['deformity_score'] is None
    mismatch=build_allocation({'rent':100},total_spending=90)
    assert mismatch['deformity_score'] is None and mismatch['visual_status']=='Source totals need review'


def test_peak_cut_recomputes_denominator_and_does_not_claim_alignment():
    value=build_allocation({'rent':200,'groceries':200,'entertainment':600})
    cut=value['reallocation_amount']
    assert cut==500 and (D(600)-cut)/(D(1000)-cut)==D('.2')
    assert not any('maintain' in message.lower() for message in value['recommendations'])

@pytest.mark.parametrize('preset,params,income,spend',[
    ('LAID_OFF_EI',(45,0,0,6),550,900),('FURNACE_REPAIR',(0,0,900,1),1000,900),
    ('LAID_OFF_AND_BILLS_UP',(45,15,0,6),550,915),('INFLATION_STAGNATION',(10,25,0,12),900,925)])
def test_presets_have_exact_parameters(preset,params,income,spend):
    r=evaluate_shock_scenario(1,scenario_id=preset,data_loader=Loader())
    p=r['shock_parameters']
    assert tuple(p[k] for k in ('income_reduction_pct','bills_increase_pct','one_off_costs','shock_duration_months'))==params
    assert r['post_shock']['income']==income and r['post_shock']['spending']==spend

@pytest.mark.parametrize('buffer,income,spending,cost,expected',[(0,0,0,0,0),(10,0,100,20,0),(100,0,100,0,1),(100,100,0,0,'no shortfall (120+)')])
def test_runway_zero_and_exhausted_edges(buffer,income,spending,cost,expected):assert calculate_runway(buffer,spending,income,cost)[0]==expected


def test_forecast_dates_income_expense_identity_and_recovery():
    history=rows(1000,900,1300)
    shock=evaluate_shock_scenario(1,scenario_id='CUSTOM',income_reduction_pct=.5,shock_duration_months=1,one_off_costs=100,data_loader=Loader(history))
    result=source_forecast(history,1000,shock)
    assert result['as_of']==date(2025,12,31) and result['projection_dates']['30']==date(2026,1,30)
    assert result['projections']['30']==D('1200')+result['income_first30']-result['expense_first30']
    assert result['projections']['90']>result['projections']['30']
    assert source_forecast([{**history[-1],'month_end_balance':None}]) is None


def test_optimization_reruns_daily_forecast():
    history=rows(500,900,1300);allocation=allocation_from_months(history)
    metrics={'account_id':1,'typical_income_I':500}
    shock=evaluate_shock_scenario(1,scenario_id='CUSTOM',data_loader=Loader(history))
    plan=source_plan(history,metrics,allocation,shock)
    for action in plan['action_plan']:
        expected=source_forecast(history,500,shock,action['monthly_savings_cad'])
        assert action['improved_balance_90']==expected['projections']['90']
        assert action['projected_runway_extension_days']==expected['runway_days']-plan['scenario']['runway_days']
        assert 'to extends' not in action['message'] and 'to improves' not in action['message']

@pytest.mark.parametrize('income,spending,balance',[(500,900,100),(1000,900,1300),(0,0,0),(1000,100,5000),(1000,900,-100)])
def test_goal_affordability_and_ceiling_timeline(income,spending,balance):
    history=rows(income,spending,balance)
    metrics={'account_id':1,'typical_income_I':income,'typical_spending_S':spending,'latest_balance':balance}
    shock=evaluate_shock_scenario(1,scenario_id='CUSTOM',data_loader=Loader(history))
    result=briefing(metrics,shock,allocation_from_months(history),months=history)['goal_plan']
    amount=result['monthly_savings']
    assert 0<=amount<=max(0,income-spending)
    assert abs(result['biweekly_savings']-amount*12/26)<=D('.005')
    remaining=result['remaining_target']
    if amount>0:
        n=result['target_months_to_complete'];assert amount*n>=remaining and amount*(n-1)<remaining
    elif remaining>0:assert result['target_months_to_complete'] is None

@pytest.mark.parametrize('rate,fee',[(0,30),(8.5,0),(12,5)])
def test_installment_payments_reconcile_and_fee_inclusive_apr(rate,fee):
    result=installment(300,fee,rate,3)
    assert sum(p['payment'] for p in result['schedule'])==result['total_repayment']
    assert result['schedule'][-1]['remaining']==0
    assert result['total_repayment']==result['principal']+result['fee']+result['total_interest']
    if fee:assert result['apr_percent']>D(str(rate))


def test_recorded_commitments_have_no_invented_dates_savings_or_duplicates():
    loader=SimpleNamespace(sources={'standing_orders':[{'order_id':1,'amount':'100','to_bank':'AB','to_account':'123','purpose':'Rent'}],
        'transactions':[{'transaction_id':n,'date':day,'amount':'100','signed_amount':'-100','partner_bank':'AB','partner_account':'123','purpose':'Rent'} for n,day in enumerate(['2025-11-01','2025-12-01'])]})
    result=recorded_commitments(loader,date(2025,12,31))
    assert len(result['subscriptions'])==1
    assert result['subscriptions'][0]['next_billing_date'] is None
    assert result['total_potential_annual_savings'] is None and result['overlap_alerts']==[]


def test_missing_cpi_does_not_substitute_a_current_value():
    value=InflationTrackerEngine(Loader([{**rows()[0],'month':'2026-01'}])).analyze_inflation_impact(1)
    assert value['period_cpi_increase_pct'] is None and value['missing_cpi_months']==['2026-01']


def test_fraud_without_history_has_no_invented_baseline_or_approval():
    value=BehavioralFraudEngine(Loader()).evaluate_transaction(1,5000,'Example',is_new_store=True)
    assert value['metrics']['z_score'] is None and value['metrics']['baseline_mean_cart'] is None
    assert value['decision']=='BELOW_REVIEW_THRESHOLD'
