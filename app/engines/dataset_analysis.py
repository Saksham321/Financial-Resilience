"""Historical source-account projections without creating personal transactions."""
from datetime import date, datetime, timezone, timedelta
from calendar import monthrange
from types import SimpleNamespace
from app.engines.calculations import D, ZERO, money, forecast, pyramid


def analyze_source_account(account, months, source_months=()):
    if not months:
        return None
    history = sorted(months, key=lambda row: row['month'])
    latest = history[-1]
    year, month = map(int, latest['month'].split('-'))
    as_of = date(year, month, monthrange(year, month)[1])
    reference = as_of + timedelta(days=1)
    balance = money(latest.get('month_end_balance', account.get('B', 0)))
    # Monthly totals feed the existing forecasting rules; no invented merchants
    # or persisted ledger transactions are required.
    aggregates = []
    for row in history:
        occurred_at = datetime.fromisoformat(row['month']+'-01').replace(tzinfo=timezone.utc)
        for amount in (D(str(row['money_in'])), -D(str(row['money_out']))):
            aggregates.append(SimpleNamespace(amount=amount, occurred_at=occurred_at,
                category='source_monthly_total', merchant='source monthly aggregate'))
    projection = forecast(aggregates, balance, [], reference)
    projection['recommendations'] = []
    projection['assumptions'] = (
        f"Historical source-account analysis as of {as_of}; projection reference {reference}. "
        "Uses the last recorded month-end balance, up to twelve completed months of income/expense totals, "
        "and spending regression. Source currency is unspecified. No current balances, future schedules, "
        "credit availability, or personal account changes are inferred.")
    full = next((r for r in source_months if r['month'] == latest['month']), latest)
    expense_rows = []
    known_total = ZERO
    for field, category in (('household_bills','household'),('insurance','insurance'),
                            ('loan_payments','loan'),('cash_withdrawals_genuine','withdrawals'),
                            ('card_withdrawals','card withdrawals')):
        amount = money(full.get(field) or 0)
        if amount > 0:
            expense_rows.append(SimpleNamespace(amount=-amount,category=category))
            known_total += amount
    spending = pyramid(expense_rows, D(str(latest['money_in'])))
    unknown = money(max(ZERO,D(str(latest['money_out']))-known_total))
    spending['unclassified_total'] = unknown
    spending['period'] = latest['month']
    spending['recommendations'] = []
    warning = 'Cash withdrawals are shown at the Peak under this application’s category policy; their final purchase purpose is unknown.'
    if unknown > 0:
        spending['deformity_score'] = None
        spending['inverted'] = False
        warning += f' {unknown} source units remain unclassified (including fees/other transfers). Pyramid ratios show classified amounts only; a complete health score is unavailable.'
    spending['warning'] = warning
    return {'account_id': account['account_id'], 'as_of': as_of.isoformat(),
            'projection_reference': reference.isoformat(), 'currency': 'Source units (currency unspecified)',
            'forecast': projection, 'pyramid': spending,
            'recommendations': ['Review the historical balance and cash flow before applying this scenario to present-day decisions.',
                'Classify remaining transfers and cash purchases to improve the expense pyramid.']}
