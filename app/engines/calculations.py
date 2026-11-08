"""Deterministic financial rules, independent of storage and external providers."""
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import radians, sin, cos, asin, sqrt
from statistics import mean, pstdev

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
    category = category.strip().casefold()
    if category != "unclassified":
        return category
    known = [t.category for t in history if t.merchant.casefold() == merchant.casefold() and t.category != "unclassified"]
    if known:
        return known[-1]
    rules = {"rent": ("rent", "landlord"), "mortgage": ("mortgage",), "loan": ("loan payment",),
             "insurance": ("insurance",), "groceries": ("grocery", "groceries", "supermarket"),
             "transportation": ("transit", "transport", "fuel", "gas station"),
             "utilities": ("electricity", "water bill", "hydro", "utilities"),
             "streaming": ("streaming",), "cloud storage": ("cloud storage",),
             "fitness": ("gym", "fitness"), "wellness": ("wellness",), "card withdrawals": ("atm", "cash withdrawal")}
    name = merchant.casefold()
    return next((key for key, phrases in rules.items() if any(p in name for p in phrases)), "unclassified")


def tier(category):
    category = category.strip().lower()
    return "base" if category in BASE else "middle" if category in MIDDLE else "peak"


def pyramid(transactions, income):
    totals = dict.fromkeys(("base", "middle", "peak"), ZERO)
    categories = defaultdict(lambda: ZERO)
    for tx in transactions:
        if tx.amount < 0:
            totals[tier(tx.category)] += -tx.amount
            categories[tx.category] += -tx.amount
    income = D(income)
    targets = {"base": 50, "middle": 30, "peak": 20}
    ratios = {key: money(value / income * 100) if income > 0 else None for key, value in totals.items()}
    recommendations = [f"Reduce {key} spending by {money(max(ZERO, totals[key] - income * D(targets[key]) / 100))} CAD per month."
                       for key in totals if income > 0 and ratios[key] > targets[key]]
    return {"income": income, "totals": totals, "actual_percent": ratios, "target_percent": targets,
            "deformity_score": sum(abs(ratios[k] - targets[k]) for k in totals) if income > 0 else None,
            "inverted": totals["peak"] > totals["base"], "categories": dict(categories),
            "recommendations": recommendations, "warning": None if income > 0 else "Ratios require positive income."}


def regression(values):
    """Ordinary least squares y=mx+b; include zero months in caller."""
    n = len(values)
    if not n:
        return ZERO, ZERO
    ys = [D(v) for v in values]
    xbar, ybar = D(n - 1) / 2, sum(ys) / n
    denominator = sum((D(x) - xbar) ** 2 for x in range(n))
    slope = sum((D(x) - xbar) * (y - ybar) for x, y in enumerate(ys)) / denominator if denominator else ZERO
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


def forecast(transactions, balance, flows, today, horizon=365, cancelled_merchants=()):
    start = add_months(today.replace(day=1), -12)
    txs = [tx for tx in transactions if start <= tx.occurred_at.date() < today.replace(day=1)]
    earliest = min((tx.occurred_at.date().replace(day=1) for tx in txs), default=today.replace(day=1))
    months = []
    cursor = earliest
    while cursor < today.replace(day=1):
        months.append(cursor.strftime("%Y-%m"))
        cursor = add_months(cursor, 1)
    expenses = {m: ZERO for m in months}
    incomes = {m: ZERO for m in months}
    category_totals = defaultdict(lambda: ZERO)
    for tx in txs:
        key = tx.occurred_at.strftime("%Y-%m")
        if tx.amount < 0:
            expenses[key] += -tx.amount
            category_totals[tx.category] += -tx.amount
        else:
            incomes[key] += tx.amount
    slope, intercept = regression(list(expenses.values()))
    income = sum(incomes.values()) / len(months) if months else ZERO
    # Scheduled categories replace their historical component to avoid double counting.
    active = [f for f in flows if f.active]
    expense_categories = {f.category for f in active if f.amount < 0}
    replaced = sum((v for k, v in category_totals.items() if k in expense_categories), ZERO) / max(1, len(months))
    replaced += sum((-t.amount for t in txs if t.amount < 0 and t.merchant.casefold() in cancelled_merchants and t.category not in expense_categories), ZERO) / max(1, len(months))
    scheduled_income = any(f.amount > 0 and f.recurrence != "once" for f in active)
    events = defaultdict(lambda: ZERO)
    for f in active:
        for day in occurrences(f, today, today + timedelta(days=horizon)):
            events[day] += f.amount
    current = D(balance) + events[today]
    zero_date = today if current <= 0 else None
    projections = {}
    path = []
    daily_expenses = []
    calendar_cash_flow = defaultdict(lambda: ZERO)
    calendar_cash_flow[today.strftime("%Y-%m")] += events[today]
    projected_shocks = []
    for offset in range(1, horizon + 1):
        day = today + timedelta(days=offset)
        month_index = len(months) + (day.year - today.year) * 12 + day.month - today.month
        spend = max(ZERO, intercept + slope * month_index - replaced)
        daily_expense = spend / monthrange(day.year, day.month)[1]
        daily_income = ZERO if scheduled_income else income / monthrange(day.year, day.month)[1]
        current += daily_income - daily_expense + events[day]
        calendar_cash_flow[day.strftime("%Y-%m")] += daily_income - daily_expense + events[day]
        if events[day] < 0 and current < 0:
            projected_shocks.append({"due_date": day, "scheduled_net_outflow": money(-events[day]), "projected_shortfall": money(-current)})
        daily_expenses.append(daily_expense)
        path.append((day, current))
        if current <= 0 and zero_date is None:
            zero_date = day
        if offset in (30, 60, 90):
            projections[str(offset)] = money(current)
    first_month_events = sum(v for day, v in events.items() if day <= today + timedelta(days=30))
    monthly_cash_flow = (ZERO if scheduled_income else income) - sum(daily_expenses[:30]) + first_month_events
    recommendations = []
    for category, total in sorted(category_totals.items(), key=lambda item: item[1], reverse=True):
        if tier(category) == "peak":
            saving = money(total / max(1, len(months)) * D("0.20"))
            improved = next((day for i, (day, value) in enumerate(path, 1) if value + saving * D(i) / 30 <= 0), None)
            recommendations.append({"category": category, "monthly_saving": saving, "action": "Reduce discretionary spending by 20%",
                                    "runway_gain_days": (improved - zero_date).days if improved and zero_date else None,
                                    "revised_zero_date": improved, "horizon_days": horizon})
    return {"balance": money(balance), "history_months": len(months), "limited_history": len(months) < 6,
            "monthly": [{"month": m, "income": money(incomes[m]), "expenses": money(expenses[m])} for m in months],
            "regression": {"slope": money(slope), "intercept": money(intercept)},
            "monthly_income": money(income), "monthly_cash_flow": money(monthly_cash_flow), "projections": projections,
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
    return {"principal": money(principal), "fee": money(fee), "annual_rate_percent": annual_rate, "months": months,
            "payment": payment, "total_interest": sum(p["interest"] for p in schedule),
            "total_repayment": sum(p["payment"] for p in schedule), "schedule": schedule}


def distance_km(lat1, lon1, lat2, lon2):
    a, b = radians(float(lat1)), radians(float(lat2))
    dlat, dlon = b - a, radians(float(lon2) - float(lon1))
    return 6371 * 2 * asin(min(1, sqrt(sin(dlat/2)**2 + cos(a)*cos(b)*sin(dlon/2)**2)))


def anomaly(amount, history, recurring_count=0, browsing_match=False, chargebacks=0,
            outside_area=False, over_budget=False, cart_size=None, hour=None, weights=None, z_threshold=3):
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
    amounts = [abs(float(t.amount)) for t in history]
    std = pstdev(amounts) if len(amounts) >= 2 else 0
    z = (float(abs(amount)) - mean(amounts)) / std if std else None
    carts = [t.cart_size for t in history if t.cart_size is not None]
    cart_std = pstdev(carts) if len(carts) > 1 else 0
    cart_z = (cart_size - mean(carts)) / cart_std if cart_size is not None and cart_std else None
    typical_hours = sorted({t.occurred_at.hour for t in history})
    score = min(D(1), max(ZERO, score))
    return {"score": score.quantize(D("0.000001")), "elevated_review": score > policy["review"] or (z is not None and z > z_threshold),
            "confirmed_fraud": False, "reasons": reasons, "amount_z_score": z, "unusually_large": z is not None and z > z_threshold,
            "cart_z_score": cart_z, "unusual_cart": cart_z is not None and cart_z > z_threshold,
            "typical_hours_utc": typical_hours, "unusual_time": bool(typical_hours) and hour not in typical_hours,
            "merchant_history_count": len(history)}


def detect_subscriptions(transactions, today):
    groups = defaultdict(list)
    for tx in transactions:
        if tx.amount < 0 and tx.occurred_at.date() <= today:
            groups[tx.merchant.strip().casefold()].append(tx)
    found = []
    for merchant, txs in groups.items():
        txs.sort(key=lambda t: t.occurred_at.replace(tzinfo=timezone.utc))
        # Collapse same-day charges, which cannot establish a recurring interval.
        unique = {t.occurred_at.date(): t for t in txs}
        txs = list(unique.values())
        if len(txs) < 2:
            continue
        intervals = [(b.occurred_at.date() - a.occurred_at.date()).days for a, b in zip(txs, txs[1:])]
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
        found.append({"merchant": merchant, "category": last.category, "amount": money(-last.amount), "cadence": cadence, "next_billing": due})
    return found


def subscription_advice(subscriptions):
    groups = defaultdict(list)
    wellness = ZERO
    for sub in subscriptions:
        if sub.status == "cancelled":
            continue
        groups[sub.category].append(sub.merchant)
        if sub.category in ("fitness", "wellness"):
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
    for q, totals in sorted(quarters.items()):
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
    return {"reference_month": reference, "quarters": output, "requires_cpi": any(q["cpi"] is None for q in output)}
