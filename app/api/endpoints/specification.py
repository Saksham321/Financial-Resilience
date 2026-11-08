"""Specification-shaped authenticated contracts alongside the existing APIs."""
from datetime import date
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.exceptions import AuthorizationError, ValidationException
from app.engines import service as svc
from app.engines.calculations import ZERO, forecast, inflation, pyramid
from app.engines.models import CPI, Offer, Subscription, Transaction
from app.engines.schemas import Input, PositiveMoney, ShockInput
from app.shared.database.models import User
from app.shared.database.session import get_db

router=APIRouter(tags=['Specification contracts'])
DB=Annotated[AsyncSession,Depends(get_db)]
Current=Annotated[User,Depends(get_current_user)]


class Mediate(Input):
    user_id:UUID|None=None
    shock_amount:PositiveMoney
    shock_type:str=Field(default='EMERGENCY_EXPENSE',min_length=1,max_length=80)
    due_date:date=Field(default_factory=date.today)


class Predictive(Input):
    window_months:int=Field(default=12,ge=6,le=12)


@router.post('/shocks/mediate')
async def mediate(req:Mediate,db:DB,user:Current,idempotency_key:Annotated[str|None,Header(max_length=100)]=None):
    if req.user_id is not None and req.user_id!=user.id:
        raise AuthorizationError('user_id must match the authenticated user')
    source='stored_snapshot'
    if settings.BANKING_API_URL and settings.BANKING_API_KEY:
        from app.api.endpoints.finance import banking_sync
        await banking_sync(db,user)
        source='banking_provider_snapshot'
    shock=await svc.create_shock(db,user.id,ShockInput(external_id='mediate:'+(idempotency_key or str(uuid4())),
        name=req.shock_type,amount=req.shock_amount,due_date=req.due_date))
    offers=[o for o in await svc.rows(db,Offer,user.id) if o.shock_id==shock.id and o.status=='proposed' and o.terms['affordable']]
    plans=[]
    for offer in offers:
        terms=offer.terms
        plans.append({'offer_id':str(offer.id),'term_months':offer.months,'monthly_installment':terms['payment'],
            'total_repayable':terms['total_repayment'],'apr':terms['apr_percent'],
            'annual_interest_rate_percent':terms['annual_rate_percent'],
            'fee_structure':{'type':'FLAT_FEE' if not float(terms['annual_rate_percent']) else 'INTEREST',
                             'amount':terms['fee'],'rate':float(terms['annual_rate_percent'])/100}})
    await db.commit()
    return {'status':'SHORTFALL_DETECTED' if shock.shortfall>0 else 'BUFFER_SUFFICIENT',
        'user_id':str(user.id),'shock_id':str(shock.id),'shortfall_amount':str(shock.shortfall),
        'banking_source':source,'credit_route':shock.routing,
        'installment_proposal':{'eligible':bool(plans),'plans':plans},'planning_only':True}


@router.post('/predictive-plan')
async def predictive(req:Predictive,db:DB,user:Current):
    txs,flows,cancelled=await svc.financial_inputs(db,user.id)
    result=forecast(txs,await svc.liquidity(db,user.id),flows,date.today(),cancelled_merchants=cancelled,window_months=req.window_months)
    if result['limited_history']:
        raise ValidationException('At least six completed months are required for this predictive contract; the dashboard provides explicitly limited-history estimates')
    return svc.encode({'user_id':str(user.id),'forecast':{'projected_zero_date':result['zero_date'],
        'current_runway_days':result['runway_days'],'trend_slope':result['regression']['slope'],
        'projections_30_60_90':result['projections']},'spending_breakdown':result['spending_breakdown'],
        'action_plan':[{'action_id':f'act_rec_{n:03d}','category':r['category'],'target_reduction_pct':0.20,
            'projected_runway_extension_days':r['runway_gain_days'],'monthly_savings':r['monthly_saving'],
            'message':r['action']} for n,r in enumerate(result['recommendations'],1)]})


@router.get('/subscriptions')
async def subscriptions(db:DB,user:Current):
    await svc.lock_user(db,user.id)
    await svc.refresh(db,user.id)
    records=svc.subscription_records(await svc.rows(db,Subscription,user.id))
    for row in records:row['cadence']=row['cadence'].upper()
    await db.commit()
    return records


@router.get('/expense-pyramid')
async def expense_pyramid(db:DB,user:Current):
    today=date.today();month=today.replace(day=1)
    txs=[t for t in await svc.rows(db,Transaction,user.id) if month<=t.occurred_at.date()<=today]
    return svc.encode(pyramid(txs,sum((t.amount for t in txs if t.amount>0),ZERO)))


@router.get('/inflation')
async def inflation_summary(db:DB,user:Current):
    return svc.encode(inflation(await svc.rows(db,Transaction,user.id),list((await db.scalars(select(CPI))).all())))
