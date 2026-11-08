"""Recorded recurring commitments, separate from illustrative demo services."""
from collections import defaultdict
from datetime import date, timedelta
from itertools import pairwise

from app.engines.calculations import D, add_months, money


def recorded_commitments(loader,as_of):
    entries=[]
    for row in loader.sources.get('standing_orders',[]):
        entries.append({'subscription_id':'order_'+str(row['order_id']),'merchant_name':row.get('purpose') or 'Standing order',
            'category':row.get('purpose') or 'Unclassified commitment','amount':float(money(row['amount'])),
            'cadence':'MONTHLY','next_billing_date':None,'notification_scheduled_for':None,
            'data_origin':'recorded_standing_order','overlap_detected':False,
            'description':'Recorded monthly standing order; its next billing date is not provided.'})
    groups=defaultdict(list)
    for row in loader.sources.get('transactions',[]):
        if D(str(row.get('signed_amount') or 0))>=0:continue
        if not row.get('partner_bank') or not row.get('partner_account'):continue
        groups[(row['partner_bank'],row['partner_account'],row.get('purpose',''))].append(row)
    notices=[]
    for (bank,counterparty,purpose),rows in groups.items():
        rows=sorted(rows,key=lambda r:r['date'])
        unique=list({r['date']:r for r in rows}.values())
        if len(unique)<2:continue
        recent=unique[-4:]
        days=[(date.fromisoformat(b['date'])-date.fromisoformat(a['date'])).days for a,b in pairwise(recent)]
        cadence='MONTHLY' if all(28<=n<=31 for n in days) else 'ANNUAL' if all(364<=n<=366 for n in days) else None
        amounts=[D(str(r['amount'])) for r in recent]
        if not cadence or max(amounts)-min(amounts)>max(amounts)*D('.10'):continue
        # Do not re-add a standing order that matches this recorded recurring payment.
        if any(r.get('to_bank')==bank and r.get('to_account')==counterparty for r in loader.sources.get('standing_orders',[])):continue
        last=date.fromisoformat(recent[-1]['date']);months=1 if cadence=='MONTHLY' else 12
        due=add_months(last,months)
        while due<as_of:due=add_months(due,months)
        key='recurring_'+str(recent[-1]['transaction_id'])
        entries.append({'subscription_id':key,'merchant_name':purpose or 'Recurring bank payment',
            'category':purpose or 'Unclassified recurring payment','amount':float(money(amounts[-1])),
            'cadence':cadence,'next_billing_date':due.isoformat(),
            'notification_scheduled_for':(due-timedelta(days=3)).isoformat(),
            'data_origin':'detected_recorded_pattern','overlap_detected':False,
            'description':'Predicted from repeated payments to the same counterparty; service identity is not established.'})
        if 0<=(due-as_of).days<=7:
            notices.append({'id':key+':'+due.isoformat(),'kind':'payment','title':'Historical recurring-payment reminder',
                'message':f'Based on records through {as_of}, a recurring payment of {money(amounts[-1])} CAD is modeled for {due}.',
                'origin':'recorded_pattern','date':due.isoformat()})
    if entries:
        notices.insert(0,{'id':'commitments','kind':'recurring','title':'Recorded recurring commitments',
            'message':f'{len(entries)} recorded orders or recurring patterns are available. Service usage and cancellation options need review.',
            'origin':'recorded_data'})
    total=sum((D(str(s['amount']))/(12 if s['cadence']=='ANNUAL' else 1) for s in entries),D(0))
    return {'subscriptions':entries,'total_active_subscriptions':len(entries),'total_monthly_recurring_spend':money(total),
        'total_potential_annual_savings':None,'overlap_alerts':[],
        'notifications':notices,'as_of':as_of.isoformat(),
        'explanation':'Amounts are recorded commitments or detected patterns, not verified digital subscriptions. No duplicate service or savings is inferred from a shared bank name.'}
