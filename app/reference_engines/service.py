"""Read-only historical analysis with shared financial models."""
from datetime import date
from math import ceil

from app.engines.calculations import D, money
from app.engines.source_planning import source_forecast, source_plan

from .data_loader import DataLoader
from .expense_pyramid import ExpensePyramidEngine
from .inflation_tracker import InflationTrackerEngine
from .metrics import compute_judge_metrics, evaluate_shock_scenario
from .recorded_subscriptions import recorded_commitments
from .shock_mediation import ShockMediationEngine


def briefing(metrics, shock, pyramid, subscriptions=None, months=None):
    income,spending,buffer=(D(str(metrics[k])) for k in ('typical_income_I','typical_spending_S','latest_balance'))
    net=income-spending
    target=money(spending*4)
    remaining=max(D(0),target-buffer)
    aspirational=money(max(D(100),income*D('.12'))) if income>0 and remaining>0 else D(0)
    affordable=money(min(max(D(0),net),aspirational,remaining))
    required=money(max(D(0),aspirational-net)) if remaining>0 else D(0)
    timeline=ceil(remaining/affordable) if affordable>0 else (0 if remaining==0 else None)
    reclaim=money(D(str(pyramid['totals']['peak']))*D('.30'))
    before=source_forecast(months,income,shock) if months else None
    after=source_forecast(months,income,shock,reclaim) if months else None
    old=before['runway_days'] if before else None
    new=after['runway_days'] if after else None
    gain=new-old if old is not None and new is not None else None
    status='Reserve target already met.' if remaining==0 else (f'Currently affordable contribution: {affordable} monthly.' if affordable>0 else 'No savings contribution is currently supported by typical cash flow.')
    actions=[status,f'Aspirational contribution: {aspirational} monthly; requires {required} of monthly spending reductions or additional income.',
             'The target is four months of typical spending. Progress uses the recorded closing balance, not the six-month average buffer.']
    if net<0:actions.append(f'First close the existing monthly cash-flow deficit of {money(-net)} before saving.')
    return {'source':'DETERMINISTIC_LOCAL_MODEL',
        'summary_text':f'Account review: typical monthly income is {income:,.2f}, spending is {spending:,.2f}, and net cash flow is {net:,.2f} CAD. The recorded closing balance is {buffer:,.2f}. Under {shock["scenario_title"]}, the constant-cost benchmark runway is {shock["post_shock"]["runway_months"]} months. Daily projections separately model the selected shock duration and recovery.',
        'goal_plan':{'headline':'Four-month resilience reserve','target_emergency_fund':target,'current_buffer':buffer,
            'remaining_target':money(remaining),'aspirational_monthly_savings':aspirational,'monthly_savings':affordable,
            'biweekly_savings':money(affordable*12/26),'required_monthly_budget_improvement':required,
            'target_months_to_complete':timeline,'action_steps':actions},
        'backup_plan':{'headline':'Shock contingency plan','immediate_actions':[
            f'Model a 30% reduction to Savings spending: {reclaim} per month. Confirm reducible purchases; transaction-type proxies are not verified discretionary services.',
            'Review recorded commitments without adding hypothetical subscription savings to the same spending cut.',
            'Request an affordability assessment and actual underwriting before accepting credit.'],
            'estimated_monthly_cashflow_improvement':reclaim,'projected_runway_gain_days':gain,
            'baseline_runway_days':old,'improved_runway_days':new,
            'baseline_balance_90':before['projections']['90'] if before else None,
            'improved_balance_90':after['projections']['90'] if after else None,
            'horizon_note':'A missing runway means no depletion within the 365-day model horizon; no fixed runway gain is assumed.'}}


async def account_review(db, account_id, scenario):
    loader=await DataLoader.for_account(db,account_id)
    result={'account_id':account_id,'profile':loader.profile,'currency':loader.profile['currency_code'] or 'CAD',
        'availability':{'financial_history':bool(loader.financial_history_available)},'as_of':None,
        'metrics':None,'shock':None,'pyramid':None,'predictive':None,'mediation':None,'inflation':None,
        'subscriptions':{'subscriptions':[],'notifications':[]},'standing_orders':[],
        'assumptions':['Imported historical data is separate from live balances and personal account records.',
            'Source amounts are Canadian dollars (CAD). No currency conversion is performed.',
            'Runway benchmark uses median income and spending and the six-month mean daily buffer at constant costs. Daily projections use the recorded closing balance, a non-negative spending trend, calendar days and shock recovery.',
            'Pyramid shares use trailing 12-month average total spending, not income. Unknown expenses remain unclassified; standing orders are not added to monthly spending.',
            'Deformity is 100 times total variation distance from 50/30/20 target shares; unavailable with incomplete categories.',
            'Credit examples do not establish eligibility, approval, benefit entitlement or disbursement.']}
    if not loader.financial_history_available:
        result['profile']['archetype_explanation']='Complete monthly history is unavailable; no financial estimates have been substituted.'
        result['briefing']={'source':'DETERMINISTIC_LOCAL_MODEL','summary_text':'Complete monthly history is unavailable. No financial estimates have been substituted.',
            'goal_plan':{'action_steps':[]},'backup_plan':{'immediate_actions':[]}}
        return result
    metrics=compute_judge_metrics(account_id,loader)
    shock=evaluate_shock_scenario(account_id,data_loader=loader,**scenario)
    result['scenario_benchmarks']=[evaluate_shock_scenario(account_id,data_loader=loader,scenario_id=key) for key in
        ('LAID_OFF_EI','FURNACE_REPAIR','LAID_OFF_AND_BILLS_UP','INFLATION_STAGNATION')]
    result['scenario_benchmarks'].append(evaluate_shock_scenario(account_id,data_loader=loader,scenario_id='CUSTOM',
        bills_increase_pct=.15,custom_label='Household bills increase 15%'))
    pyramid=ExpensePyramidEngine(loader).build_expense_pyramid(account_id)
    months=loader.monthly.to_dict(orient='records')
    predictive=source_plan(months,metrics,pyramid,shock)
    as_of=source_forecast(months,metrics['typical_income_I'])['as_of']
    subscriptions=recorded_commitments(loader,as_of if isinstance(as_of,date) else date.fromisoformat(as_of))
    shortfall=money(max(D(0),D(str(shock['post_shock']['monthly_gap'])))*shock['shock_parameters']['shock_duration_months']+D(str(shock['shock_parameters']['one_off_costs'])))
    net=metrics['net_monthly_cashflow']
    loader.profile['archetype_explanation']=(f'The imported profile is {loader.profile["archetype"]}. Recorded typical income is {metrics["typical_income_I"]:,.2f} and spending is {metrics["typical_spending_S"]:,.2f} CAD, producing a monthly '+('surplus' if net>=0 else 'deficit')+f' of {abs(net):,.2f}. The six-month mean daily buffer is {metrics["savings_buffer_B"]:,.2f}. '+('A loan record is present.' if loader.loan else 'No loan record is present.')+' These observations provide financial context; the imported label is not a credit decision.')
    inflation=InflationTrackerEngine(loader).analyze_inflation_impact(account_id)
    inflation['provenance']={'source':'CPI snapshot supplied with the comparison project; not independently verified or live Statistics Canada data',
        'last_available_month':'2025-12','comparison_period':f'{months[0]["month"]} to {months[-1]["month"]}',
        'context':'Illustrative Canadian CPI adjustment only. Currency and geographic compatibility are not established; this is not a measured change in this customer’s purchasing power.'}
    if pyramid['reallocation_amount']>0:
        subscriptions['notifications'].append({'id':'allocation-review','title':'Potential spending review','message':'Savings spending exceeds its allocation. Review hypothetical reductions below; no saving is guaranteed.','origin':'modeled_opportunity'})
    mediation=ShockMediationEngine(loader).mediate_shock(account_id,float(shortfall))
    if mediation['shortfall_amount']>0:
        subscriptions['notifications'].append({'id':'scenario-shortfall','title':'Financial shortfall detected',
            'message':f'The selected scenario has an estimated funding shortfall of {mediation["shortfall_amount"]:,.2f} CAD. Review the risk analysis; this is not a loan eligibility decision.',
            'origin':'modeled_scenario','severity':'HIGH'})
    result.update(as_of=as_of,metrics=metrics,shock=shock,pyramid=pyramid,predictive=predictive,
        mediation=mediation,subscriptions=subscriptions,
        inflation=inflation,standing_orders=loader.orders.to_dict(orient='records'),
        briefing=briefing(metrics,shock,pyramid,subscriptions,months))
    return result
