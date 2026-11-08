from datetime import datetime,timezone
from types import SimpleNamespace
from decimal import Decimal
import pytest
from app.engines.categorization import canonical_category,predict_category,category_similarity
from app.engines.calculations import tier,pyramid,anomaly,inflation
from app.engines.ai_validation import validate_prose
from app.core.exceptions import ExternalServiceError


def test_specification_category_labels_and_pyramid_contract():
    assert [tier(c) for c in ('household_bills','loan_payments','transit')]==['base','base','middle']
    transactions=[SimpleNamespace(amount=Decimal('-500'),category='household_bills'),
        SimpleNamespace(amount=Decimal('-300'),category='transit'),SimpleNamespace(amount=Decimal('-200'),category='entertainment')]
    result=pyramid(transactions,Decimal('1000'))
    assert result['deformity_score']==0 and result['visual_status']=='Close to target allocation'
    assert result['user_pyramid_ratios']=={'base':50,'middle':30,'peak':20}
    assert result['reallocation_amount']==0


def test_ml_tagger_generalizes_labelled_history_and_abstains_when_untrained():
    history=[SimpleNamespace(merchant=name,category=cat) for cat,names in (
        ('groceries',['Maple Fresh Market','Maple Fresh Foods','Maple Fresh Grocer']),
        ('transportation',['City Transit Pass','City Transit Bus','City Transit Metro'])) for name in names]
    result=predict_category('Maple Fresh Market East',history)
    assert result['category']=='groceries' and result['method']=='supervised_tfidf_naive_bayes'
    assert result['confidence']>=.65
    assert predict_category('Unknown store',[])['category']=='unclassified'


def test_category_similarity_has_fuzzy_matches_and_rejects_unrelated_tags():
    assert category_similarity('grocerie','groceries')>=.90
    assert category_similarity('CLOUD_STORAGE','cloud storage')==1
    assert category_similarity('travel','groceries')<.90
    assert category_similarity('','')==0


def test_category_time_and_cart_risks_contribute_without_disabling_other_rules():
    history=[SimpleNamespace(amount=Decimal(-v),cart_size=v,occurred_at=datetime(2026,1,1,12,tzinfo=timezone.utc)) for v in (9,10,11,9,10,11)]
    result=anomaly(Decimal('10'),history,hour=23,category_unusual=True,cart_size=100)
    assert result['score']==Decimal('.80')
    assert {'unfamiliar_category','unusual_time','unusual_cart'}<={r['rule'] for r in result['reasons']}


def test_inflation_returns_four_quarters_with_preceding_comparison_context():
    txs=[];cpi=[]
    for month in range(1,19):
        year=2025+(month-1)//12;m=(month-1)%12+1
        day=datetime(year,m,1,tzinfo=timezone.utc)
        txs.extend([SimpleNamespace(amount=Decimal(1000),occurred_at=day),SimpleNamespace(amount=Decimal(-500),occurred_at=day)])
        cpi.append(SimpleNamespace(month=day.strftime('%Y-%m'),value=Decimal(100)))
    result=inflation(txs,cpi)
    assert len(result['quarters'])==4
    assert result['quarters'][0]['real_income_growth_percent']==0


def test_generated_prose_rejects_new_numbers_and_approval_claims():
    assert validate_prose('Your buffer is 1,000 CAD.','Available liquidity: 1000.00 CAD.')
    for text in ('You have 2000 CAD.','Your loan is pre-approved.'):
        with pytest.raises(ExternalServiceError):validate_prose(text,'Available liquidity: 1000 CAD.')


def test_quarter_window_does_not_substitute_ancient_data_for_missing_quarters():
    txs=[SimpleNamespace(amount=Decimal(100),occurred_at=datetime(year,month,1,tzinfo=timezone.utc))
         for year,month in ((2020,1),(2026,1),(2026,7))]
    result=inflation(txs,[])
    assert [q['quarter'] for q in result['quarters']]==['2026-Q1','2026-Q3']
    assert result['missing_quarters']==['2025-Q4','2026-Q2']
