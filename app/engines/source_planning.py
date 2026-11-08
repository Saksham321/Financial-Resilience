"""Source-account adapters for the shared daily cash-flow forecast engine."""
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from statistics import median
from types import SimpleNamespace

from app.engines.calculations import D, forecast, money


def source_forecast(months,income=None,shock=None,reduction=0):
    rows=sorted(months,key=lambda r:r['month'])
    if not rows or rows[-1].get('month_end_balance') is None or any(row.get(key) is None for row in rows for key in ('money_in','money_out')):return None
    if income is None:income=money(median(D(str(row['money_in'])) for row in rows))
    year,month=map(int,rows[-1]['month'].split('-'))
    as_of=date(year,month,monthrange(year,month)[1])
    transactions=[]
    for row in rows:
        when=datetime.fromisoformat(row['month']+'-01').replace(tzinfo=UTC)
        for amount in (D(str(row['money_in'])),-D(str(row['money_out']))):
            transactions.append(SimpleNamespace(amount=amount,occurred_at=when,category='source monthly total',merchant='Historical monthly total'))
    scenario={}
    if shock:
        params=shock['shock_parameters']
        scenario={'one_off_costs':params['one_off_costs'],'income_multiplier':1-params['income_reduction_pct']/100,
            'extra_monthly_bills':D(str(shock['post_shock']['spending']))-D(str(shock['baseline']['spending'])),
            'duration_months':params['shock_duration_months']}
    result=forecast(transactions,D(str(rows[-1]['month_end_balance'])),[],as_of,
        history_end=as_of+timedelta(days=1),observed_months={r['month'] for r in rows},income_estimate=income,
        monthly_reduction=D(str(reduction)),scenario=scenario,generate_recommendations=False)
    result['assumptions']='Historical model projections start from the recorded closing balance on '+as_of.isoformat()+'. Monthly outflows use a non-negative linear trend and daily calendar allocation. Income uses '+result['income_assumption']+'. Scenario income and bill changes stop after the selected duration; one-off costs are deducted once. No future banking events or certain outcomes are implied.'
    return result


def source_plan(months,metrics,allocation,shock=None):
    if len(months)<2:return {'available':False,'reason':'At least two recorded months are needed for a spending trend.','forecast':None,'action_plan':[]}
    baseline=source_forecast(months,metrics['typical_income_I'])
    if baseline is None:return {'available':False,'reason':'A recorded closing balance is required.','forecast':None,'action_plan':[]}
    selected=source_forecast(months,metrics['typical_income_I'],shock)
    actions=[]
    for fraction in (D('.10'),D('.20')):
        saving=money(D(str(allocation['totals']['peak']))*fraction)
        if saving<=0:continue
        improved=source_forecast(months,metrics['typical_income_I'],shock,saving)
        old,new=selected['runway_days'],improved['runway_days']
        gain=max(0,new-old) if old is not None and new is not None else None
        outcome=(f'extend modeled runway by {gain} days' if gain is not None else
            'avoid modeled depletion within the 365-day horizon' if old is not None and new is None else
            'improve projected balances; neither model depletes within 365 days')
        actions.append({'action_id':f'peak_{int(fraction*100)}','category':'PEAK_SPENDING',
            'target_reduction_pct':float(fraction),'monthly_savings_cad':float(saving),
            'projected_runway_extension_days':gain,'baseline_runway_days':old,'improved_runway_days':new,
            'baseline_balance_90':selected['projections']['90'],'improved_balance_90':improved['projections']['90'],
            'modeled_savings_first30':money(selected['expense_first30']-improved['expense_first30']),
            'assumption':'Hypothetical cut to the Savings allocation; transaction-type proxies do not establish that purchases can be cancelled.',
            'message':f'Model a {int(fraction*100)}% Savings spending reduction ({saving} per month) to {outcome}.'})
    projections=[{'horizon_days':n,'target_date':baseline['projection_dates'][str(n)],
        'projected_balance':baseline['projections'][str(n)],'scenario_balance':selected['projections'][str(n)],
        'projected_monthly_outflow':selected['projected_monthly_outflows'][str(n)]} for n in (30,60,90)]
    return {'available':True,'account_id':metrics['account_id'],'forecast':{
        'projected_zero_date':selected['zero_date'],'current_runway_days':selected['runway_days'],
        'trend_slope':baseline['regression']['slope'],'trend_direction':'INCREASING_SPEND' if baseline['regression']['slope']>0 else 'DECREASING_SPEND' if baseline['regression']['slope']<0 else 'STABLE_SPEND',
        'linear_equation':f"y = {baseline['regression']['slope']}x + {baseline['regression']['intercept']}",
        'projections_30_60_90':projections,'reference_date':baseline['as_of'],'horizon_days':365,
        'initial_balance':baseline['recorded_balance'],'income_assumption':baseline['income_assumption'],
        'assumptions':baseline['assumptions']},'baseline':baseline,'scenario':selected,
        'spending_breakdown':{'essential_monthly':allocation['totals']['base']+allocation['totals']['middle'],
            'discretionary_monthly':allocation['totals']['peak'],'unclassified_monthly':allocation['unclassified_total'],
            'discretionary_ratio_pct':allocation['actual_percent']['peak']},'action_plan':actions}
