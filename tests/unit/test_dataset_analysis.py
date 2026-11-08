from decimal import Decimal
from app.engines.dataset_analysis import analyze_source_account


def test_historical_source_forecast_uses_month_end_and_reconciles_unknown_expenses():
    months = [{'month':f'2025-{m:02d}', 'money_in':1000, 'money_out':800,
               'month_end_balance':1200, 'household_bills':300, 'insurance':20,
               'loan_payments':80} for m in range(1,13)]
    full = [{**row, 'cash_withdrawals_genuine':'200.00', 'card_withdrawals':'50.00'} for row in months]
    result = analyze_source_account({'account_id':1,'B':99999},months,full)
    assert result['as_of']=='2025-12-31' and result['projection_reference']=='2025-12-31'
    assert result['forecast']['balance']==Decimal('1200.00')
    assert result['forecast']['history_months']==12
    assert result['forecast']['monthly_income']==Decimal('1000.00')
    assert result['forecast']['projections']['90']>Decimal('1700')
    assert result['pyramid']['totals']['base']==400
    assert result['pyramid']['totals']['peak']==50
    assert result['pyramid']['unclassified_total']==350
    assert result['pyramid']['deformity_score'] is None
    assert result['forecast']['recommendations']==[]


def test_source_accounts_produce_distinct_depletion_and_support_empty_history():
    month = {'month':'2025-12','money_in':100,'money_out':1000,'month_end_balance':50}
    result = analyze_source_account({'account_id':2},[month])
    assert 0 < result['forecast']['runway_days'] < 5
    assert result['forecast']['projections']['90']<0
    assert result['forecast']['limited_history'] is True
    assert analyze_source_account({'account_id':2},[]) is None
