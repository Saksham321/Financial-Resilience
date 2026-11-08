"""Read-only historical simulations corresponding to the supplied project ZIP."""
import base64
import json
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ExternalServiceError
from app.engines.ai_validation import validated_generated_text
from app.engines.schemas import Narrative
from app.integrations import providers
from app.integrations.gemini.client import gemini_client
from app.reference_engines.behavioral_fraud import BehavioralFraudEngine
from app.reference_engines.data_loader import DataLoader
from app.reference_engines.service import account_review
from app.shared.database.session import get_db

router=APIRouter(prefix='/source-review',tags=['Historical account analysis'])
DB=Annotated[AsyncSession,Depends(get_db)]
Finite=Annotated[float,Field(allow_inf_nan=False)]


class Scenario(BaseModel):
    model_config=ConfigDict(extra='forbid')
    scenario_id:Literal['LAID_OFF_EI','FURNACE_REPAIR','LAID_OFF_AND_BILLS_UP','INFLATION_STAGNATION','CUSTOM']='LAID_OFF_EI'
    income_reduction_pct:Annotated[Finite,Field(ge=0,le=1)]=0
    bills_increase_pct:Annotated[Finite,Field(ge=0,le=1)]=0
    one_off_costs:Annotated[Finite,Field(ge=0,le=1e9)]=0
    shock_duration_months:int=Field(default=6,ge=1,le=120)


class FraudInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    amount:Annotated[Finite,Field(gt=0,le=1e9)]
    merchant_name:str=Field(min_length=1,max_length=150)
    category:str=Field(default='RETAIL',min_length=1,max_length=80)
    is_new_store:bool=False
    recent_browsing_category:str|None=Field(default=None,max_length=80)
    is_outside_normal_location:bool=False
    is_outside_budget:bool=False
    vacation_mode:bool=False
    vacation_location:str|None=Field(default=None,max_length=150)
    chargebacks_count:int|None=Field(default=None,ge=0,le=1000)


class ExternalRequest(Scenario):
    allow_external_processing:bool=False
    profile:Literal['professional','empathetic']='professional'
    summary_text:str|None=Field(default=None,min_length=1,max_length=20000)
    generate_audio:bool=True


@router.get('/{account_id}')
async def source_review(account_id:int,db:DB):
    return await account_review(db,account_id,Scenario().model_dump())


@router.post('/{account_id}/simulate')
async def simulate(account_id:int,req:Scenario,db:DB):
    return await account_review(db,account_id,req.model_dump())


@router.post('/{account_id}/fraud')
async def fraud(account_id:int,req:FraudInput,db:DB):
    loader=await DataLoader.for_account(db,account_id)
    result=BehavioralFraudEngine(loader).evaluate_transaction(account_id,**req.model_dump())
    result['mode']='REFERENCE_SIMULATION_NO_TRANSACTION_ACTION'
    result['assumptions']='Reference model uses partner-bank counts as merchant familiarity and penalty-fee text as a chargeback proxy. Inputs are hypothetical; no browsing or location is retrieved. Vacation Mode changes location scoring only.'
    return result


async def external_briefing(account_id,req,db):
    scenario={name:getattr(req,name) for name in Scenario.model_fields}
    result=await account_review(db,account_id,scenario)
    local=result['briefing']
    if not result['availability']['financial_history']:
        return local
    if not req.allow_external_processing:
        return local
    facts={f'metric_{key}':f'{key}: {value}.' for key,value in result['metrics'].items() if key!='account_id'}
    facts['scenario']=local['summary_text']
    if result['predictive']['available']:
        facts['predictive']=f"Spending trend slope: {result['predictive']['forecast']['trend_slope']}; zero-date estimate: {result['predictive']['forecast']['projected_zero_date']}."
    facts['pyramid']=f"Reference pyramid: {result['pyramid']['visual_status']}; deformity {result['pyramid']['deformity_score']}; allocation {result['pyramid']['user_pyramid_ratios']}."
    facts['mediation']=f"Modeled shortfall: {result['mediation']['shortfall_amount']}; model status {result['mediation']['status']}. No actual approval or disbursement."
    advice=local['goal_plan']['action_steps']+local['backup_plan']['immediate_actions']
    try:
        narrative=await gemini_client.generate_structured_response(json.dumps({'verified_facts':facts,'approved_recommendations':advice}),Narrative,
            'Select supplied metric_keys and zero-based recommendation_ids. Generate conversational generated_summary grounded in selected facts and generated_actions paraphrasing selected recommendations in order. Use only supplied numbers. Never claim guaranteed results, credit approval, or disbursement. This is a historical hypothetical source-data simulation, not a live credit decision.')
        if any(k not in facts for k in narrative.metric_keys) or any(i<0 or i>=len(advice) for i in narrative.recommendation_ids):
            raise ExternalServiceError('AI selected unverified reference facts')
        generated=validated_generated_text(narrative,facts,advice)
        local={**local,'source':'GEMINI_GENERATED_GROUNDED' if generated else 'GEMINI_VERIFIED_SELECTION','summary_text':'\n\n'.join(
            [narrative.introduction]+generated+[facts[k] for k in narrative.metric_keys]+[advice[i] for i in narrative.recommendation_ids]+[narrative.closing])}
    except ExternalServiceError as exc:
        local={**local,'external_error':exc.message}
    if req.generate_audio and local['source'].startswith('GEMINI_'):
        try:
            audio=await providers.speech(local['summary_text'],req.profile)
            local={**local,'audio_base64':base64.b64encode(audio).decode('ascii'),'audio_status':'generated'}
        except ExternalServiceError as exc:
            local={**local,'audio_status':'unavailable','audio_error':exc.message}
    return local


@router.post('/{account_id}/briefing')
async def generate_briefing(account_id:int,req:ExternalRequest,db:DB):
    return await external_briefing(account_id,req,db)


@router.post('/{account_id}/audio')
async def source_audio(account_id:int,req:ExternalRequest,db:DB):
    if not req.allow_external_processing:
        raise AuthorizationError('Enable external processing before requesting ElevenLabs audio')
    scenario={name:getattr(req,name) for name in Scenario.model_fields}
    review=await account_review(db,account_id,scenario)
    audio=await providers.speech(req.summary_text or review['briefing']['summary_text'],req.profile)
    return Response(audio,media_type='audio/mpeg',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
