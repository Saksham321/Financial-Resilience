"""Source analysis uses the same allocation/forecast pipeline as the toolkit."""
from calendar import monthrange

from app.engines.expense_allocation import allocation_from_months
from app.engines.source_planning import source_forecast


def analyze_source_account(account,months,source_months=()):
    if not months:return None
    extra={row['month']:row for row in source_months}
    rows=sorted(({**row,**extra.get(row['month'],{})} for row in months),key=lambda row:row['month'])
    forecast=source_forecast(rows)
    year,month=map(int,rows[-1]['month'].split('-'))
    recorded_date=f'{year:04d}-{month:02d}-{monthrange(year,month)[1]:02d}'
    return {'account_id':account['account_id'],'as_of':recorded_date,
        'projection_reference':forecast['as_of'].isoformat() if forecast else None,
        'currency':'CAD','forecast':forecast,
        'pyramid':allocation_from_months(rows),
        'recommendations':['Review recorded spending and classify unknown purchases before relying on allocation or projections.']}
