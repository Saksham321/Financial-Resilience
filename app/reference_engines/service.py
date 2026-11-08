"""Feature/value parity with the supplied ZIP, isolated as historical simulations."""
from .data_loader import DataLoader
from .metrics import compute_judge_metrics, evaluate_shock_scenario
from .expense_pyramid import ExpensePyramidEngine
from .predictive_plan import PredictivePlanningEngine
from .shock_mediation import ShockMediationEngine
from .subscription_mgr import SubscriptionManagerEngine
from .inflation_tracker import InflationTrackerEngine


def briefing(metrics, shock, pyramid, subscriptions):
    income=metrics['typical_income_I'];spending=metrics['typical_spending_S'];buffer=metrics['savings_buffer_B']
    savings=round(max(100,income*0.12),2)
    target=round(spending*4,2)
    months=max(3,int(max(0,target-buffer)/savings))
    reclaim=metrics['discretionary_spending']*0.30+subscriptions['total_potential_annual_savings']/12
    gap=shock['post_shock']['monthly_gap']
    gain=round(min(6,max(1.5,reclaim/max(gap,100)*3)),1)
    return {'source':'DETERMINISTIC_REFERENCE_MODEL',
        'summary_text':f"Source account {metrics['account_id']}: typical monthly income {income:,.2f}, spending {spending:,.2f}, and six-month average buffer {buffer:,.2f} source units. Under {shock['scenario_title']}, modeled runway is {shock['post_shock']['runway_months']} months ({shock['post_shock']['resilience_tier']}).",
        'goal_plan':{'headline':'Four-month resilience reserve', 'target_emergency_fund':target,
            'current_buffer':buffer,'monthly_savings':savings,'biweekly_savings':round(savings/2,2),'target_months_to_complete':months,
            'action_steps':[f'Illustrative savings target: {savings} per month; assess actual affordability first.',
                f'Target reserve: {target} source units (four months of typical spending).',
                pyramid['proposed_rearrangement'].replace('$','').replace('Tangerine','reference')]},
        'backup_plan':{'headline':'Shock contingency plan',
            'immediate_actions':[f'Model a 30% discretionary reduction to {round(metrics["discretionary_spending"]*0.7,2)} per month.',
                'Review recurring commitments and distinguish recorded orders from illustrative subscription examples.',
                'Request real underwriting and an affordability assessment before accepting credit.'],
            'estimated_monthly_cashflow_improvement':round(reclaim,2),'projected_runway_gain_months':gain,
            'lifeline_recommendation':'Review modeled six-month installment terms if liquidity is depleted; these are not lender offers.'}}


async def account_review(db, account_id, scenario):
    loader=await DataLoader.for_account(db,account_id)
    metrics=compute_judge_metrics(account_id,loader)
    shock=evaluate_shock_scenario(account_id,data_loader=loader,**scenario)
    pyramid=ExpensePyramidEngine(loader).build_expense_pyramid(account_id)
    subscriptions=SubscriptionManagerEngine(loader).analyze_overlap(account_id)
    for sub in subscriptions['subscriptions']:
        sub['data_origin']='illustrative_reference_example' if not sub['subscription_id'].rsplit('_',1)[-1].isdigit() else 'recorded_standing_order'
    return {'account_id':account_id,'as_of':metrics['latest_month'],
        'currency':'Source units; reference model originally labels these CAD without conversion',
        'profile':loader.profile,'metrics':metrics,'shock':shock,
        'pyramid':pyramid,'predictive':PredictivePlanningEngine(loader).generate_predictive_plan(account_id),
        'mediation':ShockMediationEngine(loader).mediate_shock(account_id,
            shock['post_shock']['monthly_gap']*shock['shock_parameters']['shock_duration_months']+shock['shock_parameters']['one_off_costs']
            if shock['post_shock']['monthly_gap']>0 else 1500),
        'subscriptions':subscriptions,'inflation':InflationTrackerEngine(loader).analyze_inflation_impact(account_id),
        'standing_orders':loader.orders.to_dict(orient='records'),
        'briefing':briefing(metrics,shock,pyramid,subscriptions),
        'assumptions':['Historical reference calculations from the supplied ZIP; not live balances or underwriting.',
            'Subscription examples and January 2026 billing dates are illustrative and do not establish actual subscriptions.',
            'CPI uses the ZIP-provided 2020–2025 snapshot, not the live CPI feed.',
            'Reference pyramid uses 12-month average shares of spending; the original overview uses last-month shares of income.',
            'Modeled shock duration is reported; the reference runway formula does not model income recovery after that duration.']}
