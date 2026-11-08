"""Deterministic financial rules, independent of storage and external providers."""
from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise
from math import asin, cos, radians, sin, sqrt
from statistics import mean, pstdev

from app.engines.categorization import canonical_category, predict_category

D = Decimal
ZERO = D("0")


def money(value):
    return D(str(value)).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def add_months(day, count):
    month = day.month - 1 + count
    year = day.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


BASE = {"household", "rent", "mortgage", "loan", "insurance", "household bills", "loan payments"}
MIDDLE = {"groceries", "transportation", "utilities", "basic utilities"}


def classify(merchant, category="unclassified", history=()):
    """Prefer supplied categories, then user merchant history, then transparent text rules."""
    category = canonical_category(category)
    if category != "unclassified":
        return category
    known = [t.category for t in history if t.merchant.casefold() == merchant.casefold() and t.category != "unclassified"]
    if known:
        return canonical_category(known[-1])
    rules = {"rent": ("rent", "landlord"), "mortgage": ("mortgage",), "loan": ("loan payment",),
             "insurance": ("insurance",), "groceries": ("grocery", "groceries", "supermarket"),
             "transportation": ("transit", "transport", "fuel", "gas station"),
             "utilities": ("electricity", "water bill", "hydro", "utilities"),
             "streaming": ("streaming",), "cloud storage": ("cloud storage",),
             "fitness": ("gym", "fitness"), "wellness": ("wellness",), "card withdrawals": ("atm", "cash withdrawal")}
    name = merchant.casefold()
    matched=next((key for key, phrases in rules.items() if any(p in name for p in phrases)),None)
    return matched or predict_category(merchant,history)['category']


def tier(category):
    from app.engines.expense_allocation import category_level
    return category_level(category)


def pyramid(transactions, income):
    from app.engines.expense_allocation import build_allocation
    amounts = defaultdict(lambda: ZERO)
    for tx in transactions:
        if tx.amount < 0:
            amounts[canonical_category(tx.category)] += -tx.amount
    return build_allocation(amounts,income)


def regression(values,x_values=None):
    """Ordinary least squares y=mx+b; include zero months in caller."""
    n = len(values)
    if not n:
        return ZERO, ZERO
    ys = [D(v) for v in values]
    xs=[D(x) for x in (range(n) if x_values is None else x_values)]
    if len(xs)!=n:raise ValueError('Regression coordinates must have equal lengths')
    xbar, ybar = sum(xs)/n, sum(ys) / n
    denominator = sum((x-xbar)**2 for x in xs)
    slope = sum((x-xbar)*(y-ybar) for x,y in zip(xs,ys))/denominator if denominator else ZERO
    return slope, ybar - slope * xbar


def occurrences(flow, start, end):
    """Expand calendar schedules from their original day (no February drift)."""
    due = flow.due_date
    i = 0
    while due <= end:
        if due >= start and (not flow.end_date or due <= flow.end_date):
            yield due
        if flow.recurrence == "once":
            break
        i += 1
        due = add_months(flow.due_date, i * (12 if flow.recurrence == "annual" else 1))


def forecast(transactions, balance, flows, today, horizon=365, cancelled_merchants=(),window_months=12,
             history_end=None,observed_months=None,income_estimate=None,monthly_reduction=ZERO,scenario=None,
             generate_recommendations=True):
    if not 6<=window_months<=12:
        raise ValueError('Forecast window must be 6–12 months')
    cutoff=history_end or today.replace(day=1)
    start = add_months(cutoff, -window_months)
    txs = [tx for tx in transactions if start <= tx.occurred_at.date() < cutoff]
    earliest = min((tx.occurred_at.date().replace(day=1) for tx in txs), default=cutoff)
    months = []
    cursor = earliest
    while cursor < cutoff:
        key=cursor.strftime('%Y-%m')
        if observed_months is None or key in observed_months:months.append(key)
        cursor = add_months(cursor, 1)
    expenses = {m: ZERO for m in months}
    incomes = {m: ZERO for m in months}
    category_totals = defaultdict(lambda: ZERO)
    for tx in txs:
        key = tx.occurred_at.strftime("%Y-%m")
        if tx.amount < 0:
            expenses[key] += -tx.amount
            category_totals[canonical_category(tx.category)] += -tx.amount
        else:
            incomes[key] += tx.amount
    coordinates=[(int(m[:4])-earliest.year)*12+int(m[5:])-earliest.month for m in months]
    slope, intercept = regression(list(expenses.values()),coordinates)
    income = D(str(income_estimate)) if income_estimate is not None else sum(incomes.values()) / len(months) if months else ZERO
    # Scheduled categories replace their historical component to avoid double counting.
    active = [f for f in flows if f.active]
    expense_categories = {canonical_category(f.category) for f in active if f.amount < 0}
    replaced = sum((v for k, v in category_totals.items() if k in expense_categories), ZERO) / max(1, len(months))
    replaced += sum((-t.amount for t in txs if t.amount < 0 and t.merchant.casefold() in cancelled_merchants and canonical_category(t.category) not in expense_categories), ZERO) / max(1, len(months))
    scheduled_income = any(f.amount > 0 and f.recurrence != "once" for f in active)
    events = defaultdict(lambda: ZERO)
    for f in active:
        for day in occurrences(f, today, today + timedelta(days=horizon)):
            events[day] += f.amount
    scenario=scenario or {}
    one_off=D(str(scenario.get('one_off_costs',0)))
    income_multiplier=D(str(scenario.get('income_multiplier',1)))
    extra_bills=D(str(scenario.get('extra_monthly_bills',0)))
    shock_end=add_months(today+timedelta(days=1),int(scenario.get('duration_months',0)))
    current = D(balance) + events[today]-one_off
    zero_date = today if current <= 0 else None
    projections = {}
    projected_monthly_outflows={}
    path = []
    daily_expenses = []
    daily_incomes=[]
    calendar_cash_flow = defaultdict(lambda: ZERO)
    calendar_cash_flow[today.strftime("%Y-%m")] += events[today]
    projected_shocks = []
    for offset in range(1, horizon + 1):
        day = today + timedelta(days=offset)
        month_index = (day.year-earliest.year)*12+day.month-earliest.month
        spend = max(ZERO, intercept + slope * month_index - replaced-D(str(monthly_reduction)))
        in_shock=day<shock_end
        if in_shock:spend+=extra_bills
        daily_expense = spend / monthrange(day.year, day.month)[1]
        daily_income = ZERO if scheduled_income else income*(income_multiplier if in_shock else D(1))/monthrange(day.year,day.month)[1]
        current += daily_income - daily_expense + events[day]
        calendar_cash_flow[day.strftime("%Y-%m")] += daily_income - daily_expense + events[day]
        if events[day] < 0 and current < 0:
            projected_shocks.append({"due_date": day, "scheduled_net_outflow": money(-events[day]), "projected_shortfall": money(-current)})
        daily_expenses.append(daily_expense)
        daily_incomes.append(daily_income)
        path.append((day, current))
        if current <= 0 and zero_date is None:
            zero_date = day
        if offset in (30, 60, 90):
            projections[str(offset)] = money(current)
            projected_monthly_outflows[str(offset)]=money(spend)
    first_month_events = sum(v for day, v in events.items() if day <= today + timedelta(days=30))
    monthly_cash_flow = sum(daily_incomes[:30]) - sum(daily_expenses[:30]) + first_month_events
    recommendations = []
    for category, total in sorted(category_totals.items(), key=lambda item: item[1], reverse=True) if generate_recommendations else []:
        if tier(category) == "peak":
            saving = money(total / max(1, len(months)) * D("0.20"))
            changed=forecast(transactions,balance,flows,today,horizon,cancelled_merchants,window_months,
                history_end,observed_months,income_estimate,D(str(monthly_reduction))+saving,scenario,False)
            improved=changed['zero_date']
            recommendations.append({"category": category, "monthly_saving": saving, "action": "Reduce discretionary spending by 20%",
                                    "runway_gain_days": (improved - zero_date).days if improved and zero_date else None,
                                    "revised_zero_date": improved, "horizon_days": horizon,
                                    "baseline_balance_90":projections.get('90'),"improved_balance_90":changed['projections'].get('90')})
    essential=sum(v for category,v in category_totals.items() if tier(category) in ('base','middle'))/max(1,len(months))
    discretionary=sum(v for category,v in category_totals.items() if tier(category)=='peak')/max(1,len(months))
    return {"balance": money(D(balance)-one_off),"recorded_balance":money(balance),"as_of":today,
            "projection_dates":{str(n):today+timedelta(days=n) for n in (30,60,90)},
            "income_assumption":"specified historical median" if income_estimate is not None else "mean of observed completed months",
            "expense_first30":money(sum(daily_expenses[:30])),"income_first30":money(sum(daily_incomes[:30])),
            "history_months": len(months), "limited_history": len(months) < 6,
            "spending_breakdown":{"essential_monthly":money(essential),"discretionary_monthly":money(discretionary)},
            "monthly": [{"month": m, "income": money(incomes[m]), "expenses": money(expenses[m])} for m in months],
            "regression": {"slope": money(slope), "intercept": money(intercept)},
            "monthly_income": money(income), "monthly_cash_flow": money(monthly_cash_flow), "projections": projections,
            "projected_monthly_outflows":projected_monthly_outflows,
            "zero_date": zero_date, "runway_days": (zero_date - today).days if zero_date else None,
            "horizon_days": horizon, "end_balance": money(current), "recommendations": recommendations,
            "calendar_cash_flow": {month: money(value) for month, value in calendar_cash_flow.items()}, "projected_shocks": projected_shocks,
            "assumptions": "Calendar schedules replace historical spending in the same category; scheduled income replaces historical income. Balance is an as-of-now snapshot; history is not reapplied."}


def installment(principal, fee, annual_rate, months):
    principal, fee, annual_rate = D(principal), D(fee), D(annual_rate)
    if principal <= 0 or fee < 0 or annual_rate < 0 or months not in (3, 6, 12):
        raise ValueError("Invalid installment terms")
    financed = principal + fee
    rate = annual_rate / 1200
    payment = money(financed * rate / (1 - (1 + rate) ** -months) if rate else financed / months)
    remaining = financed
    schedule = []
    for number in range(1, months + 1):
        interest = money(remaining * rate)
        due = money(remaining + interest) if number == months else min(payment, money(remaining + interest))
        repaid = due - interest
        remaining = money(remaining - repaid)
        schedule.append({"number": number, "payment": due, "principal": repaid, "interest": interest, "remaining": remaining})
    low,high=D(0),D(1)
    def present_value(rate):return sum(row['payment']/(1+rate)**row['number'] for row in schedule)
    while present_value(high)>principal:high*=2
    if sum(row['payment'] for row in schedule)<=principal:apr=D(0)
    else:
        for _ in range(80):
            middle=(low+high)/2
            if present_value(middle)>principal:low=middle
            else:high=middle
        apr=money((low+high)/2*12*100)
    return {"principal": money(principal), "fee": money(fee), "annual_rate_percent": annual_rate,"apr_percent":apr,
            "apr_method":"12 × monthly internal rate of return on net principal and cent-reconciled payments; illustrative, not a regulated quote", "months": months,
            "payment": payment, "total_interest": sum(p["interest"] for p in schedule),
            "total_repayment": sum(p["payment"] for p in schedule), "schedule": schedule}


def distance_km(lat1, lon1, lat2, lon2):
    a, b = radians(float(lat1)), radians(float(lat2))
    dlat, dlon = b - a, radians(float(lon2) - float(lon1))
    return 6371 * 2 * asin(min(1, sqrt(sin(dlat/2)**2 + cos(a)*cos(b)*sin(dlon/2)**2)))


def anomaly(amount, history, recurring_count=0, browsing_match=False, chargebacks=0,
            outside_area=False, over_budget=False, cart_size=None, hour=None, weights=None, z_threshold=3,
            category_unusual=False,baseline_history=None):
    policy = {"new": D("0.50"), "familiar": D("0.50"), "recurring": D("0.90"), "browsing": D("0.15"),
              "chargeback": D("0.10"), "geography": D("0.25"), "budget": D("0.10"), "review": D("0.85")}
    policy.update({k: D(str(v)) for k, v in (weights or {}).items()})
    score = policy["familiar"] if history else policy["new"]
    reasons = [{"rule": "familiar_merchant" if history else "new_merchant", "score": score}]
    for _ in range(recurring_count):
        score *= policy["recurring"]
    if recurring_count:
        reasons.append({"rule": "recurring", "count": recurring_count, "score": score})
    if browsing_match:
        score = max(ZERO, score - policy["browsing"])
        reasons.append({"rule": "browsing_match", "adjustment": -policy["browsing"]})
    for rule, adjustment in (("chargebacks", policy["chargeback"] * chargebacks),
                             ("outside_area", policy["geography"] if outside_area else ZERO),
                             ("over_budget", policy["budget"] if over_budget else ZERO)):
        score += adjustment
        if adjustment:
            reasons.append({"rule": rule, "adjustment": adjustment})
    baseline=history if baseline_history is None else baseline_history
    amounts = [abs(float(t.amount)) for t in baseline]
    std = pstdev(amounts) if len(amounts) >= 2 else 0
    z = (float(abs(amount)) - mean(amounts)) / std if std else None
    carts = [t.cart_size for t in baseline if t.cart_size is not None]
    cart_std = pstdev(carts) if len(carts) > 1 else 0
    cart_z = (cart_size - mean(carts)) / cart_std if cart_size is not None and cart_std else None
    typical_hours = sorted({t.occurred_at.hour for t in baseline})
    unusual_time=bool(typical_hours) and hour not in typical_hours
    for rule,enabled in (("unfamiliar_category",category_unusual),
                         ("unusual_time",unusual_time and len(baseline)>=6),
                         ("unusual_cart",cart_z is not None and cart_z>z_threshold)):
        if enabled:
            adjustment=D(str((weights or {}).get(rule,'0.10')))
            score+=adjustment;reasons.append({"rule":rule,"adjustment":adjustment})
    score = min(D(1), max(ZERO, score))
    return {"score": score.quantize(D("0.000001")), "elevated_review": score > policy["review"] or (z is not None and z > z_threshold),
            "confirmed_fraud": False, "reasons": reasons, "amount_z_score": z, "unusually_large": z is not None and z > z_threshold,
            "cart_z_score": cart_z, "unusual_cart": cart_z is not None and cart_z > z_threshold,
            "typical_hours_utc": typical_hours, "unusual_time": unusual_time,
            "merchant_history_count": len(history),"amount_mean":round(mean(amounts),6) if amounts else None,
            "amount_standard_deviation":round(std,6),"cart_standard_deviation":round(cart_std,6)}


def detect_subscriptions(transactions, today):
    groups = defaultdict(list)
    for tx in transactions:
        if tx.amount < 0 and tx.occurred_at.date() <= today:
            groups[tx.merchant.strip().casefold()].append(tx)
    found = []
    for merchant, txs in groups.items():
        txs.sort(key=lambda t: t.occurred_at.replace(tzinfo=UTC))
        # Collapse same-day charges, which cannot establish a recurring interval.
        unique = {t.occurred_at.date(): t for t in txs}
        txs = list(unique.values())
        if len(txs) < 2:
            continue
        intervals = [(b.occurred_at.date() - a.occurred_at.date()).days for a, b in pairwise(txs)]
        recent = intervals[-3:]
        cadence = "monthly" if all(28 <= n <= 31 for n in recent) else "annual" if all(364 <= n <= 366 for n in recent) else None
        amounts = [abs(t.amount) for t in txs[-4:]]
        if cadence is None or max(amounts) - min(amounts) > max(amounts) * D("0.10"):
            continue
        last = txs[-1]
        months = 1 if cadence == "monthly" else 12
        n = 1
        due = add_months(last.occurred_at.date(), months)
        while due < today:
            n += 1
            due = add_months(last.occurred_at.date(), months * n)
        found.append({"merchant": merchant, "category": canonical_category(last.category), "amount": money(-last.amount), "cadence": cadence, "next_billing": due})
    return found


def subscription_advice(subscriptions):
    groups = defaultdict(list)
    wellness = ZERO
    for sub in subscriptions:
        if sub.status == "cancelled":
            continue
        category=canonical_category(sub.category)
        groups[category].append(sub.merchant)
        if category in ("fitness", "wellness"):
            wellness += sub.amount / (12 if sub.cadence == "annual" else 1)
    advice = [f"Review overlapping {c}: {', '.join(names)}." for c, names in groups.items() if len(names) > 1]
    if wellness > 150:
        advice.append(f"Fitness and wellness total {money(wellness)} CAD monthly, exceeding 150 CAD.")
    return advice


def inflation(transactions, observations):
    cpi = {r.month: D(r.value) for r in observations}
    quarters = defaultdict(lambda: {"income": ZERO, "expenses": ZERO, "months": set()})
    for tx in transactions:
        day = tx.occurred_at.date()
        q = f"{day.year}-Q{(day.month-1)//3+1}"
        quarters[q]["income" if tx.amount > 0 else "expenses"] += abs(tx.amount)
        quarters[q]["months"].add(day.strftime("%Y-%m"))
    reference = max(cpi, default=None)
    output = []
    previous = None
    last_index=max((int(q[:4])*4+int(q[-1]) for q in quarters),default=None)
    selected=[(q,totals) for q,totals in sorted(quarters.items()) if last_index is not None and int(q[:4])*4+int(q[-1])>=last_index-4]
    for q, totals in selected:
        year, number = int(q[:4]), int(q[-1])
        months = [f"{year}-{m:02}" for m in range((number-1)*3+1, number*3+1)]
        # Never silently substitute a CPI period or compare incomplete CPI quarters.
        qcpi = sum(cpi[m] for m in months) / 3 if all(m in cpi for m in months) else None
        factor = cpi[reference] / qcpi if qcpi and reference else None
        real_income = money(totals["income"] * factor) if factor else None
        real_expenses = money(totals["expenses"] * factor) if factor else None
        row = {"quarter": q, "nominal_income": money(totals["income"]), "nominal_expenses": money(totals["expenses"]),
               "real_income": real_income, "real_expenses": real_expenses, "cpi": qcpi,
               "incomplete_transactions": len(totals["months"]) < 3, "alerts": []}
        consecutive = previous and (int(previous["quarter"][:4])*4+int(previous["quarter"][-1]) + 1 == year*4+number)
        if consecutive and not row["incomplete_transactions"] and not previous["incomplete_transactions"] and real_income is not None and previous["real_income"] is not None:
            ig = (real_income / previous["real_income"] - 1) * 100 if previous["real_income"] > 0 else None
            eg = (real_expenses / previous["real_expenses"] - 1) * 100 if previous["real_expenses"] > 0 else None
            row.update(real_income_growth_percent=money(ig) if ig is not None else None, real_expense_growth_percent=money(eg) if eg is not None else None)
            if ig is not None and ig < 0:
                row["alerts"].append("Wage stagnation: purchasing power declined.")
            if ig is not None and eg is not None and eg > ig and real_expenses > real_income:
                row["alerts"].append("Overspending: real expenses exceed income and are growing faster.")
        output.append(row)
        previous = row
    output=[row for row in output if int(row['quarter'][:4])*4+int(row['quarter'][-1])>=last_index-3]
    expected=[f'{(index-1)//4}-Q{(index-1)%4+1}' for index in range(last_index-3,last_index+1)] if last_index is not None else []
    return {"reference_month": reference, "quarters": output,"missing_quarters":[q for q in expected if q not in quarters],
            "requires_cpi": any(q["cpi"] is None for q in output)}
