"""Shared orchestration; all queries are scoped to the authenticated user."""
import json
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select, update, or_
from sqlalchemy.exc import IntegrityError
from fastapi.encoders import jsonable_encoder
from app.core.config import settings
from app.core.exceptions import ExternalServiceError, ValidationException, EntityNotFoundError
from app.core.logging import logger
from app.shared.database.models import BankAccount, UserPreference, UserConsent, FinancialDecision, AuditLog, User
from app.engines.models import Transaction, PrivacySetting, ScheduledFlow, Forecast, Subscription, Notification, Budget, Vacation, Chargeback, Shock, Offer, CPI
from app.engines.calculations import forecast, pyramid, inflation, detect_subscriptions, subscription_advice, anomaly, distance_km, add_months, installment, D, ZERO, money, occurrences, classify
from app.integrations import providers


def encode(value):
    return jsonable_encoder(value, custom_encoder={Decimal: str, datetime: lambda v: (v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)).isoformat()})


def record(row):
    result=encode({c.key: getattr(row, c.key) for c in row.__table__.columns if c.key not in ("audio", "hashed_password")})
    if 'audio' in row.__table__.columns:
        result['audio_available']=row.audio is not None
    return result


async def rows(db, model, uid):
    return list((await db.scalars(select(model).where(model.user_id == uid))).all())


async def owned(db, model, uid, identifier, lock=False):
    query = select(model).where(model.user_id == uid, model.id == identifier)
    if lock:
        query = query.with_for_update()
    row = await db.scalar(query)
    if row is None:
        raise EntityNotFoundError("Record not found")
    return row


async def lock_user(db, uid):
    await db.scalar(select(User).where(User.id == uid).with_for_update())


async def preferences(db, uid):
    return await db.scalar(select(UserPreference).where(UserPreference.user_id == uid))


async def privacy(db, uid):
    return await db.scalar(select(PrivacySetting).where(PrivacySetting.user_id == uid))


async def notify(db, uid, key, title, message, scheduled_for=None):
    existing = await db.scalar(select(Notification).where(Notification.user_id == uid, Notification.dedupe_key == key))
    if existing:
        if scheduled_for is not None and existing.scheduled_for is None:
            existing.scheduled_for=scheduled_for
        return existing
    row = Notification(user_id=uid, dedupe_key=key, title=title, message=message,scheduled_for=scheduled_for)
    db.add(row)
    await db.flush()
    return row


async def liquidity(db, uid):
    accounts = await rows(db, BankAccount, uid)
    return sum((a.available_balance for a in accounts if a.is_active and a.currency == "CAD" and a.account_type in ("CHECKING", "SAVINGS","CASH")), ZERO)


async def financial_inputs(db, uid):
    txs = await rows(db, Transaction, uid)
    flows = await rows(db, ScheduledFlow, uid)
    subscriptions = await rows(db, Subscription, uid)
    names = {f.name.casefold() for f in flows if f.active and f.amount < 0}
    from types import SimpleNamespace
    for sub in subscriptions:
        if sub.status != "cancelled" and sub.merchant not in names:
            flows.append(SimpleNamespace(due_date=sub.next_billing, end_date=None, recurrence=sub.cadence,
                                         amount=-sub.amount, category=sub.category, active=True))
    return txs, flows, [s.merchant for s in subscriptions if s.status == "cancelled"]


async def refresh(db, uid, today=None):
    today = today or date.today()
    await db.flush()
    txs = await rows(db, Transaction, uid)
    subscriptions = await rows(db, Subscription, uid)
    for item in detect_subscriptions(txs, today):
        row = next((s for s in subscriptions if s.merchant == item["merchant"] and s.cadence == item["cadence"]), None)
        if row is None:
            row = Subscription(user_id=uid, **item, status="active")
            db.add(row)
            subscriptions.append(row)
        elif row.status != "cancelled":
            for k, v in item.items():
                setattr(row, k, v)
    await db.flush()
    txs, flows, cancelled = await financial_inputs(db, uid)
    active_reminders=set()
    for sub in subscriptions:
        if sub.status != "cancelled":
            key=f"billing:{sub.id}:{sub.next_billing}"
            active_reminders.add(key)
            due=datetime.combine(sub.next_billing-timedelta(days=3),datetime.min.time(),tzinfo=timezone.utc)
            await notify(db, uid, f"billing:{sub.id}:{sub.next_billing}", "Upcoming subscription charge",
                         f"{sub.merchant}: {sub.amount} CAD expected on {sub.next_billing}.",scheduled_for=due)
    for notice in await rows(db,Notification,uid):
        if notice.dedupe_key.startswith('billing:'):
            notice.cancelled=notice.dedupe_key not in active_reminders
    metrics = encode(forecast(txs, await liquidity(db, uid), flows, today, cancelled_merchants=cancelled))
    snapshot = await db.scalar(select(Forecast).where(Forecast.user_id == uid))
    if snapshot is None:
        db.add(Forecast(user_id=uid, metrics=metrics))
    else:
        snapshot.metrics = metrics
    # A projected depletion event creates one alert per date, never a debt or a fabricated credit decision.
    if metrics["zero_date"]:
        await notify(db, uid, f"runway:{metrics['zero_date']}", "Projected liquidity shortfall",
                     f"Available funds are projected to reach zero on {metrics['zero_date']}. Review upcoming obligations.")
    active_runway=f"runway:{metrics['zero_date']}" if metrics['zero_date'] else None
    for notice in await rows(db,Notification,uid):
        if notice.dedupe_key.startswith('runway:'):
            notice.cancelled=notice.dedupe_key!=active_runway
    await db.flush()
    return metrics


async def dashboard(db, uid):
    await lock_user(db, uid)
    projection = await refresh(db, uid)
    txs = await rows(db, Transaction, uid)
    current_month = date.today().replace(day=1)
    month = [t for t in txs if t.occurred_at.date() >= current_month]
    income = sum((t.amount for t in month if t.amount > 0), ZERO)
    subs = await rows(db, Subscription, uid)
    cpi = list((await db.scalars(select(CPI))).all())
    return {"forecast": projection, "pyramid": encode(pyramid(month, income)), "inflation": encode(inflation(txs, cpi)),
            "subscriptions": subscription_records(subs), "subscription_recommendations": subscription_advice(subs),
            "fraud_alerts": [record(t) for t in txs if t.fraud.get("elevated_review")],
            "notifications": [record(n) for n in (await db.scalars(select(Notification).where(Notification.user_id==uid,
                Notification.cancelled.is_(False),or_(Notification.scheduled_for.is_(None),Notification.scheduled_for<=datetime.now(timezone.utc))))).all()],
            "shocks": [record(s) for s in await rows(db, Shock, uid)], "offers": [record(o) for o in await rows(db, Offer, uid)],
            "integration_status": integration_status()}


def subscription_records(subscriptions):
    output=[]
    for sub in subscriptions:
        peers=[s for s in subscriptions if s.id!=sub.id and s.status!='cancelled' and s.category==sub.category]
        output.append({**record(sub),'subscription_id':str(sub.id),'merchant_name':sub.merchant,
            'next_billing_date':sub.next_billing.isoformat(),
            'notification_scheduled_for':(sub.next_billing-timedelta(days=3)).isoformat(),
            'overlap_detected':sub.status!='cancelled' and bool(peers),
            'overlapping_subscription_ids':[str(s.id) for s in peers] if sub.status!='cancelled' else []})
    return output


def integration_status():
    result = {name.lower(): "configured_unverified" if getattr(settings, name + "_API_URL") and getattr(settings, name + "_API_KEY") else "requires_configuration"
              for name in ("BANKING", "UNDERWRITING", "BROWSING", "NOTIFICATION")}
    result.update(gemini="configured_unverified" if settings.GEMINI_API_KEY else "requires_credentials",
                  elevenlabs="configured_unverified" if settings.ELEVENLABS_API_KEY else "requires_credentials",
                  statistics_canada="public_api_available_not_probed", banking_data="manually_entered_balances",
                  architecture="modular_monolith", lending="planning_only_no_disbursement")
    return result


async def ingest(db, uid, req):
    await lock_user(db, uid)
    from app.engines.categorization import canonical_category
    req=req.model_copy(update={'category':canonical_category(req.category)})
    existing = await db.scalar(select(Transaction).where(Transaction.user_id == uid, Transaction.external_id == req.external_id))
    if existing:
        if req.category == "unclassified":
            req = req.model_copy(update={"category": canonical_category(existing.category)})
        # Retrying the same event is safe; reusing the key for a different event is not.
        if existing.account_id != req.account_id or existing.amount != req.amount or existing.merchant != req.merchant or canonical_category(existing.category) != req.category or existing.occurred_at.replace(tzinfo=timezone.utc) != req.occurred_at:
            raise ValidationException("Transaction external_id already belongs to a different event")
        return existing
    account = await owned(db, BankAccount, uid, req.account_id)
    if not account.is_active or account.currency != "CAD":
        raise ValidationException("Transaction requires an active CAD account")
    pref, geo = await preferences(db, uid), await privacy(db, uid)
    if req.latitude is not None and (not geo or not geo.geolocation_consent):
        raise ValidationException("Geolocation processing requires explicit consent")
    prior = [t for t in await rows(db, Transaction, uid) if t.occurred_at.replace(tzinfo=timezone.utc) < req.occurred_at]
    req = req.model_copy(update={"category": classify(req.merchant, req.category, prior)})
    txs=[t for t in prior if t.occurred_at.replace(tzinfo=timezone.utc)>=req.occurred_at-timedelta(days=90)]
    history = [t for t in txs if t.merchant.casefold() == req.merchant and t.amount < 0]
    history.sort(key=lambda t: t.occurred_at.replace(tzinfo=timezone.utc))
    recurring = 0
    sequence = sorted([t for t in prior if t.merchant.casefold()==req.merchant and t.amount<0],key=lambda t:t.occurred_at) + [req]
    for a, b in zip(sequence, sequence[1:]):
        days = (b.occurred_at.date() - a.occurred_at.date()).days
        if (28 <= days <= 31 or 364 <= days <= 366) and abs(abs(b.amount) - abs(a.amount)) <= abs(a.amount) * D("0.10"):
            recurring += 1
    match, warnings = False, []
    if pref and pref.consent_browsing_context and req.amount < 0:
        try:
            match = await providers.browsing(uid, req.category, req.occurred_at)
        except ExternalServiceError as exc:
            warnings.append(exc.message)
            logger.warning("browsing_context_unavailable", user_id=str(uid))
    cbs = [c for c in await rows(db, Chargeback, uid) if add_months(req.occurred_at.date(), -3) <= c.reported_on <= req.occurred_at.date()]
    budgets = await rows(db, Budget, uid)
    budget = next((b for b in budgets if canonical_category(b.category) == req.category), None)
    spent = sum((-t.amount for t in txs if t.amount < 0 and canonical_category(t.category) == req.category and t.occurred_at.strftime("%Y-%m") == req.occurred_at.strftime("%Y-%m")), ZERO)
    outside, vacation = False, None
    if geo and geo.geolocation_consent and req.latitude is not None:
        vacations = await rows(db, Vacation, uid)
        vacation = next((v for v in vacations if v.enabled and v.start_date <= req.occurred_at.date() <= v.end_date and distance_km(v.latitude, v.longitude, req.latitude, req.longitude) <= float(v.radius_km)), None)
        if vacation is None:
            centers = [(geo.home_latitude, geo.home_longitude)] if geo.home_latitude is not None else []
            centers += [(t.latitude, t.longitude) for t in txs if t.latitude is not None and not t.vacation_id and not t.fraud.get("elevated_review") and not any(r.get("rule") == "outside_area" for r in t.fraud.get("reasons", []))]
            if centers:
                outside = all(distance_km(lat, lon, req.latitude, req.longitude) > float(geo.radius_km) for lat, lon in centers)
            else:
                warnings.append("No normal spending area established yet.")
    weights = {"new": settings.FRAUD_NEW_MERCHANT, "familiar": settings.FRAUD_FAMILIAR_MERCHANT,
               "recurring": settings.FRAUD_RECURRING_MULTIPLIER, "browsing": settings.FRAUD_BROWSING_REDUCTION,
               "chargeback": settings.FRAUD_CHARGEBACK_INCREMENT, "geography": settings.FRAUD_GEOGRAPHY_INCREMENT,
               "budget": settings.FRAUD_BUDGET_INCREMENT, "review": settings.FRAUD_REVIEW_THRESHOLD,
               "unfamiliar_category":settings.FRAUD_CATEGORY_INCREMENT,"unusual_time":settings.FRAUD_TIME_INCREMENT,
               "unusual_cart":settings.FRAUD_CART_INCREMENT}
    baseline=[t for t in txs if t.amount<0]
    categories={canonical_category(t.category) for t in baseline}
    result = anomaly(req.amount, history, recurring, match, len(cbs), outside,
                     bool(budget and spent + abs(req.amount) > budget.monthly_amount), req.cart_size, req.occurred_at.hour, weights, settings.FRAUD_Z_THRESHOLD,
                     category_unusual=len(baseline)>=6 and req.category not in categories,baseline_history=baseline) if req.amount < 0 else {"score": 0, "elevated_review": False, "confirmed_fraud": False, "reasons": []}
    result['baseline_window_days']=90
    result['baseline_transaction_count']=len(baseline)
    from collections import Counter
    result['behavioral_profile']={'window_start':(req.occurred_at-timedelta(days=90)).isoformat(),
        'window_end':req.occurred_at.isoformat(),
        'category_distribution':dict(Counter(canonical_category(t.category) for t in baseline)),
        'hour_distribution_utc':dict(Counter(str(t.occurred_at.hour) for t in baseline)),
        'geographic_history_count':sum(t.latitude is not None for t in baseline) if geo and geo.geolocation_consent else 0}
    result.update(warnings=warnings, category_familiarity_count=sum(t.category == req.category for t in txs), geography_evaluated=bool(geo and geo.geolocation_consent and req.latitude is not None))
    row = Transaction(user_id=uid, **req.model_dump(), vacation_id=vacation.id if vacation else None, fraud=encode(result))
    db.add(row)
    await db.flush()
    if result["elevated_review"]:
        await notify(db, uid, f"fraud:{row.id}", "Transaction needs review", f"Review {row.merchant}: {abs(row.amount)} CAD. This is an anomaly flag, not confirmed fraud.")
    db.add(AuditLog(user_id=uid, event_type="TRANSACTION_INGESTED", details={"transaction_id": str(row.id)}))
    from app.engines.platform import publish_financial_event
    await publish_financial_event(db, uid, f"transaction:{row.id}", "transaction_ingested",
                                  {"transaction_id": str(row.id)})
    # Imported history does not mutate a current balance snapshot. Banking sync replaces snapshots explicitly.
    await refresh(db, uid)
    return row


async def vacation_view(db, uid, vacation):
    geo = await privacy(db, uid)
    txs = [t for t in await rows(db, Transaction, uid) if t.vacation_id == vacation.id]
    total = sum((-t.amount for t in txs if t.amount < 0), ZERO)
    view = record(vacation)
    if not geo or not geo.geolocation_consent:
        for key in ("latitude", "longitude"):
            view.pop(key, None)
    return {**view, "total_spent": str(money(total)), "remaining_budget": str(money(vacation.budget - total)),
            "transactions": [record(t) for t in txs]}


async def associate_trip(db, uid, vacation):
    """Associate previously imported, consented coordinates without rewriting historical risk decisions."""
    if not vacation.enabled:
        return
    for tx in await rows(db, Transaction, uid):
        if tx.latitude is None or tx.longitude is None:
            continue
        eligible = vacation.start_date <= tx.occurred_at.date() <= vacation.end_date and distance_km(vacation.latitude, vacation.longitude, tx.latitude, tx.longitude) <= float(vacation.radius_km)
        if eligible and tx.vacation_id in (None, vacation.id):
            tx.vacation_id = vacation.id
        elif not eligible and tx.vacation_id == vacation.id:
            tx.vacation_id = None


async def create_shock(db, uid, req):
    await lock_user(db, uid)
    existing = await db.scalar(select(Shock).where(Shock.user_id == uid, Shock.external_id == req.external_id))
    if existing:
        if existing.amount != req.amount or existing.due_date != req.due_date:
            raise ValidationException("Shock external_id belongs to a different event")
        return existing
    txs, flows, cancelled = await financial_inputs(db, uid)
    days = max(0, (req.due_date - date.today()).days)
    # Compute liquidity at the actual obligation date, including prior scheduled commitments.
    projected = forecast(txs, await liquidity(db, uid), flows, date.today(), horizon=days, cancelled_merchants=cancelled)
    available = D(projected["end_balance"])
    shortfall = money(max(ZERO, req.amount - available))
    row = Shock(user_id=uid, **req.model_dump(), shortfall=shortfall, routing={"status": "not_required"})
    db.add(row)
    await db.flush()
    db.add(ScheduledFlow(user_id=uid, external_id=f"shock:{row.id}", name=req.name, category="shock", amount=-req.amount,
                         due_date=req.due_date, recurrence="once", active=True))
    if shortfall > 0:
        try:
            decision = await providers.underwriting(uid, shortfall, str(row.id))
            row.routing = {"status": "conventional_credit" if decision["eligible"] else "installments", "decision": decision}
        except ExternalServiceError as exc:
            row.routing = {"status": "eligibility_unknown", "error": exc.message}
        if row.routing["status"] == "installments":
            await generate_offers(db, uid, row)
    await notify(db, uid, f"shock:{row.id}", "Financial shock detected", f"{row.name}: shortfall {shortfall} CAD; routing {row.routing['status']}.")
    await refresh(db, uid)
    return row


async def generate_offers(db, uid, shock):
    if settings.INSTALLMENT_ANNUAL_RATE is None or settings.INSTALLMENT_FEE is None:
        shock.routing = {**shock.routing, "offers_status": "requires_configured_rate_and_fee"}
        return
    for months in (3, 6, 12):
        capacity = await repayment_capacity(db, uid, shock, months)
        terms = installment(shock.shortfall, D(str(settings.INSTALLMENT_FEE)), D(str(settings.INSTALLMENT_ANNUAL_RATE)), months)
        if terms['payment']>capacity:
            continue
        terms.update(affordable=True, monthly_capacity=capacity, planning_only=True)
        db.add(Offer(user_id=uid, shock_id=shock.id, months=months, terms=encode(terms), status="proposed", expires_on=date.today() + timedelta(days=7)))
    await db.flush()
    available=await db.scalar(select(Offer.id).where(Offer.shock_id==shock.id).limit(1))
    if available is None:
        shock.routing={**shock.routing,'offers_status':'no_affordable_plan','message':'No 3/6/12-month payment fits projected capacity. Review expenses or obtain qualified assistance.'}


async def repayment_capacity(db, uid, shock, months):
    """Conservative minimum monthly capacity over the repayment term, including other obligations."""
    txs, flows, cancelled = await financial_inputs(db, uid)
    flows = [f for f in flows if getattr(f, "external_id", None) != f"shock:{shock.id}"]
    projection = forecast(txs, await liquidity(db, uid), flows, date.today(), horizon=800, cancelled_merchants=cancelled)
    # Repayments begin one month after the shock, so evaluate those calendar months.
    capacities = [D(projection["calendar_cash_flow"].get(add_months(shock.due_date, n).strftime("%Y-%m"), "0")) for n in range(1, months + 1)]
    return max(ZERO, min(capacities, default=ZERO))


async def decide(db, uid, offer_id, req):
    await lock_user(db, uid)
    offer = await owned(db, Offer, uid, offer_id, lock=True)
    if offer.status == req.decision:
        return offer
    if offer.status != "proposed":
        raise ValidationException("Offer already decided or superseded")
    if offer.expires_on < date.today():
        raise ValidationException("Offer has expired")
    if req.decision == "accepted":
        if not req.confirm_obligation:
            raise ValidationException("Explicit confirmation of repayment obligations is required")
        # Recheck current capacity; an earlier offer is never sufficient proof of affordability.
        shock = await owned(db, Shock, uid, offer.shock_id)
        capacity = await repayment_capacity(db, uid, shock, offer.months)
        if D(offer.terms["payment"]) > max(ZERO, capacity):
            raise ValidationException("Offer is no longer affordable under the current forecast")
        if shock.due_date < date.today():
            raise ValidationException("Shock due date has passed; reassessment required")
        # This activates a local repayment plan. No provider disbursement is fabricated.
        for payment in offer.terms["schedule"]:
            db.add(ScheduledFlow(user_id=uid, external_id=f"offer:{offer.id}:{payment['number']}", name="Accepted repayment plan",
                                 category="loan", amount=-D(payment["payment"]), due_date=add_months(shock.due_date, payment["number"]),
                                 recurrence="once", active=True, source_offer_id=offer.id))
        db.add(ScheduledFlow(user_id=uid, external_id=f"offer:{offer.id}:funding", name="Planned financing (not disbursed)", category="financing",
                             amount=D(offer.terms["principal"]), due_date=shock.due_date, recurrence="once", active=True, source_offer_id=offer.id))
        for other in await rows(db, Offer, uid):
            if other.shock_id == offer.shock_id and other.id != offer.id and other.status == "proposed":
                other.status = "superseded"
    offer.status = req.decision
    db.add(FinancialDecision(user_id=uid, decision_type="LOAN_OFFER", status=req.decision.upper(), inputs={"offer_id": str(offer.id)}, outputs=offer.terms,
                             notes="User-confirmed local plan. Lender activation/disbursement requires an external lending contract."))
    await refresh(db, uid)
    return offer
