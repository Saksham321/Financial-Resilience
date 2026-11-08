from datetime import date, datetime, timezone
from decimal import Decimal as D
from types import SimpleNamespace as NS
import pytest
from app.engines.calculations import installment, anomaly, regression, forecast, pyramid, inflation, detect_subscriptions, subscription_advice, add_months, occurrences, distance_km, classify


def tx(amount, day=date(2026, 1, 1), merchant="merchant", category="entertainment", cart=1):
    return NS(amount=D(str(amount)), occurred_at=datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc), merchant=merchant, category=category, cart_size=cart)


def flow(amount, due, recurrence="once", category="rent", end=None):
    return NS(amount=D(str(amount)), due_date=due, recurrence=recurrence, category=category, active=True, end_date=end)


@pytest.mark.parametrize("months", [3, 6, 12])
@pytest.mark.parametrize("rate", ["0", "6.75", "24.99"])
def test_amortization_exact(months, rate):
    result = installment(D("1234.56"), D("12.34"), D(rate), months)
    schedule = result["schedule"]
    assert schedule[-1]["remaining"] == 0
    assert sum(row["principal"] for row in schedule) == D("1246.90")
    assert result["total_repayment"] == D("1246.90") + result["total_interest"]
    assert len(schedule) == months
    assert all(row["payment"] >= 0 and row["remaining"] >= 0 for row in schedule)


@pytest.mark.parametrize("args", [(0,0,0,3),(100,-1,0,3),(100,0,-1,3),(100,0,0,5)])
def test_invalid_installment(args):
    with pytest.raises(ValueError):
        installment(*(D(a) if i < 3 else a for i,a in enumerate(args)))


def test_new_merchant_baseline():
    assert anomaly(D(10), [])['score'] == D('.50')


@pytest.mark.parametrize("count", [1,2,3,10])
def test_recurrence_multiplicative(count):
    assert anomaly(D(10), [], recurring_count=count)['score'] == (D('.50') * D('.90')**count).quantize(D('.000001'))


@pytest.mark.parametrize("kwargs,expected", [({"browsing_match":True},'.35'),({"chargebacks":1},'.60'),({"chargebacks":3},'.80'),({"outside_area":True},'.75'),({"over_budget":True},'.60')])
def test_every_fraud_adjustment(kwargs, expected):
    assert anomaly(D(10), [], **kwargs)['score'] == D(expected)


def test_fraud_clamps_and_review():
    assert anomaly(D(10), [], chargebacks=20)['score'] == 1
    assert anomaly(D(10), [], recurring_count=100, browsing_match=True)['score'] == 0
    assert not anomaly(D(10), [], weights={"new":'.85'})['elevated_review']
    result=anomaly(D(10), [], chargebacks=4)
    assert result['elevated_review'] and not result['confirmed_fraud']


def test_z_score_cart_and_time():
    history=[tx(-v, cart=v) for v in [9,10,11,10,9,11]]
    result=anomaly(D(100), history, cart_size=100, hour=23)
    assert result['amount_z_score'] > 3 and result['unusually_large']
    assert result['unusual_cart'] and result['unusual_time']
    assert anomaly(D(100),[tx(-10),tx(-10)])['amount_z_score'] is None


def test_regression():
    assert regression([D(10),D(20),D(30)]) == (D(10),D(10))
    assert regression([]) == (D(0),D(0))
    assert regression([D(5)]) == (D(0),D(5))


def test_forecast_schedules_and_no_double_count():
    today=date(2026,7,1)
    history=[tx(-100,date(2026,m,5),category="rent") for m in range(1,7)]
    result=forecast(history,D(100),[flow(-100,date(2026,7,5),"monthly")],today)
    assert result['history_months']==6 and not result['limited_history']
    assert result['projections']['30']==0
    assert result['zero_date']==date(2026,7,5)
    assert result['projections']['60']==-100


def test_forecast_income_and_upcoming_obligation():
    result=forecast([],D(0),[flow(1000,date(2026,7,2),"monthly","income"),flow(-500,date(2026,7,3))],date(2026,7,1))
    assert result['projections']['30']==500
    assert result['runway_days']==0
    assert result['limited_history']


@pytest.mark.parametrize("balance",[0,-100,100])
def test_no_history(balance):
    result=forecast([],D(balance),[],date(2026,1,1))
    assert result['projections']['90']==balance
    assert result['runway_days']==(0 if balance<=0 else None)


def test_month_end_schedule_no_drift():
    result=list(occurrences(flow(-10,date(2026,1,31),'monthly'),date(2026,1,1),date(2026,4,30)))
    assert result==[date(2026,1,31),date(2026,2,28),date(2026,3,31),date(2026,4,30)]


def test_pyramid_exact_targets():
    result=pyramid([tx(-500,category='insurance'),tx(-300,category='groceries'),tx(-200)],D(1000))
    assert result['deformity_score']==0
    assert not result['inverted']
    result=pyramid([tx(-600),tx(-100,category='rent')],D(1000))
    assert result['deformity_score']==D('65.71') and result['inverted']
    assert pyramid([tx(-10)],D(0))['deformity_score']==D('80.00')


@pytest.mark.parametrize("interval,cadence",[(28,'monthly'),(30,'monthly'),(31,'monthly'),(365,'annual'),(366,'annual'),(20,None),(60,None)])
def test_recurring_detection(interval,cadence):
    from datetime import timedelta
    a=date(2024,1,1);b=a+timedelta(days=interval)
    result=detect_subscriptions([tx(-20,a),tx(-20,b)],b)
    assert (result[0]['cadence'] if result else None)==cadence


def test_familiar_recurring_merchant_keeps_specified_initial_baseline():
    assert anomaly(D(10),[tx(-10)],recurring_count=1)['score']==D('.45')


def test_duplicate_same_day_and_unstable_amount_not_subscription():
    assert detect_subscriptions([tx(-10),tx(-10)],date(2026,2,1))==[]
    assert detect_subscriptions([tx(-10),tx(-100,date(2026,1,31))],date(2026,2,1))==[]


def test_subscription_overlap_and_wellness():
    subs=[NS(status='active',category=c,merchant=str(i),amount=D(a),cadence='monthly') for i,(c,a) in enumerate([('streaming',20),('streaming',30),('cloud storage',10),('cloud storage',15),('fitness',100),('wellness',60)])]
    advice=subscription_advice(subs)
    assert len(advice)==3


def test_inflation_constant_reference_and_alerts():
    txs=[tx(100,date(2026,m,1)) for m in range(1,7)]+[tx(-a,date(2026,m,2)) for m,a in [(1,100),(2,100),(3,100),(4,150),(5,150),(6,150)]]
    obs=[NS(month=f'2026-{m:02}',value=D(100 if m<=3 else 110)) for m in range(1,7)]
    result=inflation(txs,obs)
    q1,q2=result['quarters']
    assert result['reference_month']=='2026-06'
    assert q1['real_income']==330 and q2['real_income']==300
    assert q2['real_income_growth_percent']==D('-9.09')
    assert len(q2['alerts'])==2


def test_inflation_missing_cpi_and_zero_income():
    result=inflation([tx(-20)],[])
    assert result['requires_cpi'] and result['quarters'][0]['real_income'] is None
    assert inflation([],[])['quarters']==[]


def test_distance():
    assert distance_km(0,0,0,0)==0
    assert 110 < distance_km(0,0,1,0) < 112


def test_category_inference_and_history():
    assert classify('Local supermarket')=='groceries'
    assert classify('Unknown shop',history=[tx(-10,merchant='Unknown shop',category='insurance')])=='insurance'
    assert classify('Unknown shop')=='unclassified'
    assert classify('Supermarket','transportation')=='transportation'


def test_one_time_funding_does_not_replace_historical_income():
    history=[tx(100,date(2026,m,5)) for m in range(1,7)]
    result=forecast(history,D(100),[flow(500,date(2026,7,2),category='financing')],date(2026,7,1))
    assert result['projections']['30'] > 690


def test_today_obligations_and_cancelled_subscriptions():
    result=forecast([],D(100),[flow(-150,date(2026,7,1))],date(2026,7,1))
    assert result['projections']['30']==-50 and result['runway_days']==0
    history=[tx(-100,date(2026,m,5)) for m in range(1,7)]
    result=forecast(history,D(100),[],date(2026,7,1),cancelled_merchants=['merchant'])
    assert result['projections']['90']==100


def test_recommendation_estimates_runway_impact():
    history=[tx(-100,date(2026,m,5)) for m in range(1,7)]
    result=forecast(history,D(100),[],date(2026,7,1))
    recommendation=result['recommendations'][0]
    assert recommendation['monthly_saving']==D('20')
    assert recommendation['runway_gain_days'] > 0


def test_partial_quarter_does_not_issue_false_wage_alert():
    transactions=[tx(100,date(2026,m,1)) for m in range(1,5)]
    obs=[NS(month=f'2026-{m:02}',value=D(100)) for m in range(1,7)]
    result=inflation(transactions,obs)
    assert result['quarters'][-1]['incomplete_transactions']
    assert result['quarters'][-1]['alerts']==[]
