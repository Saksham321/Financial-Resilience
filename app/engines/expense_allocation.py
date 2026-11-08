"""One spending-based expense allocation model for all dashboard/API views."""
from decimal import Decimal

from app.engines.categorization import canonical_category

TARGETS={'base':Decimal(50),'middle':Decimal(30),'peak':Decimal(20)}
TOLERANCE=Decimal(5)
BASE={'household','rent','mortgage','loan','insurance','household bills','loan payments'}
MIDDLE={'groceries','transportation','utilities','basic utilities'}
PEAK={'entertainment','card withdrawals','unknown transfers','discretionary','dining',
      'streaming','cloud storage','fitness','wellness','shopping','retail','travel','luxury goods'}


def category_level(category):
    category=canonical_category(category)
    return 'base' if category in BASE else 'middle' if category in MIDDLE else 'peak' if category in PEAK else 'unclassified'


def threshold_state(actual,target,tolerance=TOLERANCE):
    if actual is None:return 'unknown'
    difference=Decimal(str(target))-Decimal(str(actual))
    return 'over' if difference<0 else 'near' if difference<=tolerance else 'below'


def build_allocation(categories,income=None,total_spending=None,provenance=None,period=None):
    from app.engines.calculations import money
    zero=Decimal(0)
    grouped={key:zero for key in (*TARGETS,'unclassified')}
    cleaned={}
    for category,amount in categories.items():
        value=Decimal(str(amount))
        if not value.is_finite() or value<0:raise ValueError('Expense category amounts must be finite and non-negative')
        name=canonical_category(category)
        cleaned[name]=cleaned.get(name,zero)+value
        grouped[category_level(name)]+=value
    category_total=sum(grouped.values(),zero)
    total=Decimal(str(total_spending)) if total_spending is not None else category_total
    if not total.is_finite() or total<0:raise ValueError('Total spending must be finite and non-negative')
    mismatch=category_total-total
    invalid=mismatch>Decimal('.005')
    if not invalid:
        grouped['unclassified']+=max(zero,total-category_total)
        # Exact shares use the component sum when sub-cent averaging differences exist.
        total=sum(grouped.values(),zero)
    percentages={key:money(grouped[key]/total*100) if total>0 and not invalid else None for key in TARGETS}
    unknown=grouped['unclassified']
    complete=total>0 and not invalid and unknown<Decimal('.005')
    score=money(sum(abs(grouped[k]/total-TARGETS[k]/100) for k in TARGETS)*50) if complete else None
    inverted=grouped['peak']>grouped['base']
    if invalid:status='Source totals need review'
    elif total<=0:status='No spending recorded'
    elif not complete:status='Needs categorization'
    elif inverted:status='Inverted Pyramid (Critical Risk)'
    elif score>35:status='Large allocation imbalance'
    elif score>18:status='Allocation needs review'
    else:status='Close to target allocation'
    excess={k:money(max(zero,grouped[k]-total*TARGETS[k]/100)) for k in TARGETS}
    # Removing Savings spend changes both the numerator and the spending denominator.
    # (Savings-cut)/(total-cut)=20% -> cut=(Savings-20%*total)/(1-20%).
    cut=money(max(zero,(grouped['peak']-total*Decimal('.20'))/Decimal('.80'))) if not invalid else zero
    recommendations=[]
    if invalid:recommendations.append('Review category totals before relying on the allocation; components exceed recorded spending.')
    elif not complete:recommendations.append('Categorize remaining cash withdrawals, fees and other unknown expenses before assessing the full spending structure.')
    if cut>0:
        recommendations.append(f'Model reducing Savings spending by {cut} per month to reach 20% of the reduced spending total. Confirm which purchases can actually be reduced.')
    if excess['base']>0:
        recommendations.append('Needs costs exceed their 50% allocation. Review fixed commitments without missing required loan, insurance or household payments.')
    if excess['middle']>0:
        recommendations.append('Wants costs exceed their 30% allocation. Review necessary living costs while protecting essentials.')
    if complete and not any(excess.values()):recommendations.append('The recorded spending allocation is close to the targets. Affordability still depends on income and commitments.')
    income_value=Decimal(str(income)) if income is not None else None
    warnings=[]
    if income_value is not None and total>income_value:
        warnings.append(f'Recorded spending exceeds income by {money(total-income_value)}. Allocation balance does not imply affordable cash flow.')
    if unknown>=Decimal('.005'):warnings.append('Unclassified spending is shown separately and is not assumed to be discretionary.')
    if provenance and any(v=='transaction_type_proxy' for v in provenance.values()):
        warnings.append('Some allocations use transaction-type proxies rather than verified purchase purposes.')
    return {'income':money(income_value) if income_value is not None else None,
        'totals':{k:money(grouped[k]) for k in TARGETS},'categories':{k:money(v) for k,v in cleaned.items()},
        'total_spending':money(total),'unclassified_total':money(unknown),
        'unclassified_percent':money(unknown/total*100) if total>0 and not invalid else None,
        'actual_percent':percentages,'target_percent':TARGETS,'user_pyramid_ratios':percentages,
        'income_allocation_percent':{k:money(grouped[k]/income_value*100) if income_value is not None and income_value>0 else None for k in TARGETS},
        'denominator':'total_spending','period':period,'deformity_score':score,'deformity_max':100,
        'score_method':'100 × total variation distance: ½ × sum of absolute differences between actual and target spending shares. Unavailable when spending is unclassified or inconsistent.',
        'inverted':inverted,'visual_status':status,'recommendations':recommendations,
        'proposed_rearrangement':recommendations[0] if recommendations else 'Review the available spending history.',
        'reallocation_amount':cut,'excess_amounts':excess,'provenance':provenance or {},
        'levels':[{'key':k,'amount':money(grouped[k]),'actual_percent':percentages[k],'target_percent':TARGETS[k],
                   'state':threshold_state(percentages[k],TARGETS[k])} for k in ('peak','middle','base')],
        'warning':' '.join(warnings) or None}


def allocation_from_months(months,income=None):
    """Trailing-average source allocation; standing orders are never added again."""
    from app.engines.calculations import D
    rows=sorted(months,key=lambda r:r['month'])[-12:]
    if not rows:return build_allocation({},income=income)
    fields={'household_bills':'household bills','insurance':'insurance','loan_payments':'loan payments',
            'groceries':'groceries','transit':'transportation','basic_utilities':'basic utilities',
            'card_withdrawals':'card withdrawals','transfers_out_other':'unknown transfers',
            'cash_withdrawals_genuine':'unclassified','bank_fees':'unclassified'}
    amounts={};provenance={}
    for field,category in fields.items():
        value=sum((D(str(row.get(field) or 0)) for row in rows),D(0))/len(rows)
        amounts[category]=amounts.get(category,D(0))+value
        provenance[category]='transaction_type_proxy' if field in ('card_withdrawals','transfers_out_other') else 'unclassified' if category=='unclassified' else 'recorded_category'
    total=sum((D(str(row['money_out'])) for row in rows),D(0))/len(rows)
    return build_allocation(amounts,income,total,provenance,
        period=f"{rows[0]['month']} to {rows[-1]['month']}")
