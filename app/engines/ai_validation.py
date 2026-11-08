"""Validate generated prose against selected, server-verified numeric facts."""
import re
from decimal import Decimal
from app.core.exceptions import ExternalServiceError

NUMBER=re.compile(r'(?<![\w])[-+]?\d[\d,]*(?:\.\d+)?')
UNSUPPORTED=re.compile(r'\b(guaranteed|pre[- ]?approved|risk[- ]?free|funding approved|funds disbursed|loan approved)\b',re.I)


def numbers(text):
    return {Decimal(match.replace(',','')) for match in NUMBER.findall(text)}


def validate_prose(text,evidence):
    if UNSUPPORTED.search(text) or not numbers(text).issubset(numbers(evidence)):
        raise ExternalServiceError('AI prose included unverified numbers or a financial guarantee/approval')
    return text


def validated_generated_text(result,facts,advice):
    if any(k not in facts for k in result.metric_keys) or any(i<0 or i>=len(advice) for i in result.recommendation_ids):
        raise ExternalServiceError('AI response referenced unverified financial information')
    parts=[]
    if result.generated_summary:
        parts.append(validate_prose(result.generated_summary,' '.join(facts[k] for k in result.metric_keys)))
    if len(result.generated_actions)>len(result.recommendation_ids):
        raise ExternalServiceError('AI action text lacks a selected recommendation')
    for text,index in zip(result.generated_actions,result.recommendation_ids):
        parts.append(validate_prose(text,advice[index]))
    return parts
