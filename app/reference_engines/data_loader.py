"""Request-scoped adapter for the reviewed ZIP calculations; reads our database.

Only the requested account's monthly/transaction records are loaded. The ZIP's
singleton, raw file paths, network clients, and startup behavior are not used.
"""
import pandas as pd
from sqlalchemy import select
from app.shared.database.datasets import DatasetSourceRecord as Record
from app.api.endpoints.datasets import DATASET_ID
from app.core.exceptions import EntityNotFoundError, ValidationException


class DataLoader:
    @classmethod
    def get_instance(cls, *args, **kwargs):
        raise RuntimeError('Reference calculations require an explicit database snapshot')

    @classmethod
    async def for_account(cls, db, account_id):
        self = cls()
        self.account_id = account_id
        rows = (await db.scalars(select(Record).where(Record.dataset_id == DATASET_ID,
            Record.account_id == account_id))).all()
        self.sources = {}
        for row in rows:
            self.sources.setdefault(row.source, []).append(row.payload)
        if not self.sources.get('accounts'):
            raise EntityNotFoundError('Source account not found in imported CSV records')
        if not self.sources.get('monthly_summary'):
            raise ValidationException('Source account has no monthly history')
        self.monthly = pd.DataFrame(self.sources['monthly_summary']).sort_values('month')
        for column in self.monthly.columns:
            if column != 'month':
                self.monthly[column] = pd.to_numeric(self.monthly[column], errors='raise')
        self.transactions = pd.DataFrame(self.sources.get('transactions', []))
        if not self.transactions.empty:
            self.transactions = self.transactions.sort_values(['date','transaction_id'])
            self.transactions['amount'] = pd.to_numeric(self.transactions['amount'])
            for column in ('partner_bank','purpose'):
                self.transactions[column] = self.transactions[column].replace('',None)
        self.orders = pd.DataFrame(self.sources.get('standing_orders', []))
        if not self.orders.empty:
            self.orders['amount'] = pd.to_numeric(self.orders['amount'])
            self.orders['order_id'] = pd.to_numeric(self.orders['order_id'])
        self.loan = None
        if self.sources.get('loans'):
            self.loan = dict(self.sources['loans'][-1])
            for field in ('amount','monthly_payment','duration_months','defaulted'):
                self.loan[field] = float(self.loan[field])
            self.loan['is_active_end_2025'] = self.loan['status'] in ('C','D')
        account = self.sources['accounts'][0]
        async def source_row(source, key):
            record = await db.get(Record,(DATASET_ID,source,str(key)))
            return record.payload if record else {}
        branch = await source_row('districts',account['district_id'])
        owner = next((r for r in self.sources.get('dispositions',[]) if r['type']=='owner'),{})
        client = await source_row('clients',owner.get('client_id',''))
        home = await source_row('districts',client.get('district_id',account['district_id']))
        cards = []
        disposition_ids = {r['disposition_id'] for r in self.sources.get('dispositions',[])}
        # Card records have disposition IDs rather than account IDs.
        all_cards = (await db.scalars(select(Record).where(Record.dataset_id==DATASET_ID,Record.source=='cards'))).all()
        for row in all_cards:
            r=row.payload
            if r['disposition_id'] in disposition_ids:
                cards.append({'card_id':int(r['card_id']),'card_type':r['card_type'],'issued':r['issued']})
        self.profile = {'account_id':account_id,'client_id':client.get('client_id'),
            'account_opened':account['account_opened'],'statement_frequency':account['frequency'],
            'gender':client.get('gender','Unknown'),'birth_date':client.get('birth_date','Unknown'),
            'branch_district_name':branch.get('district_name','Unknown'),
            'home_district_name':home.get('district_name','Unknown'),'region':home.get('region','Unknown'),
            'average_salary':float(home.get('average_salary',0)),
            'unemployment_rate_2023':float(home.get('unemployment_rate_2023',0)),
            'cards':cards,'has_loan':self.loan is not None,'loan':self.loan}
        return self

    def get_account_profile(self, account_id):
        return self.profile

    def get_monthly_summary(self, account_id):
        return self.monthly.copy()

    def get_account_transactions(self, account_id):
        return self.transactions.copy()

    def get_standing_orders(self, account_id):
        return self.orders.copy()

    def get_loan(self, account_id):
        return self.loan
