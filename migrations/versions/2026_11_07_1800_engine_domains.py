"""Frozen financial domain schema; no runtime model imports.

Revision ID: engine_domains_v1
Revises: 95c6cf829e7c
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from app.shared.database import base

revision = "engine_domains_v1"
down_revision = "95c6cf829e7c"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    pg = bind.dialect.name == "postgresql"
    if pg:
        for schema in ("core", "transactions", "shock_mediation", "predictive_planning", "behavioral_fraud", "subscriptions", "inflation", "ai"):
            op.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
        # Align only legacy CHAR identifiers; never alter already-UUID referenced columns.
        for schema, names in (("core", ("users", "user_profiles", "bank_accounts", "financial_goals", "user_preferences")),
                              ("audit", ("system_events", "financial_decisions", "user_consents"))):
            for name in names:
                columns = {c["name"]: c["type"] for c in sa.inspect(bind).get_columns(name, schema=schema)}
                for column in ("id", "user_id"):
                    if column in columns and not isinstance(columns[column], UUID):
                        op.execute(f'ALTER TABLE {schema}.{name} ALTER COLUMN {column} TYPE uuid USING {column}::uuid')
    if not sa.inspect(bind).has_table("cpi_observations", schema="inflation" if pg else None):
        op.create_table('cpi_observations',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('month', sa.String(length=7), nullable=False),
        sa.Column('value', sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_cpi_observations')),
        sa.UniqueConstraint('month', name=op.f('uq_cpi_observations_month')),
        schema='inflation'
        )
    if not sa.inspect(bind).has_table("verified_summaries", schema="ai" if pg else None):
        op.create_table('verified_summaries',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('text', sa.String(length=20000), nullable=False),
        sa.Column('audio', sa.LargeBinary(), nullable=True),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_verified_summaries_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_verified_summaries')),
        schema='ai'
        )
        op.create_index(op.f('ix_ai_verified_summaries_user_id'), 'verified_summaries', ['user_id'], unique=False, schema='ai')
    if not sa.inspect(bind).has_table("chargebacks", schema="behavioral_fraud" if pg else None):
        op.create_table('chargebacks',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('external_id', sa.String(length=150), nullable=False),
        sa.Column('reported_on', sa.Date(), nullable=False),
        sa.Column('merchant', sa.String(length=150), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_chargebacks_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chargebacks')),
        sa.UniqueConstraint('user_id', 'external_id', name=op.f('uq_chargebacks_user_id')),
        schema='behavioral_fraud'
        )
        op.create_index(op.f('ix_behavioral_fraud_chargebacks_user_id'), 'chargebacks', ['user_id'], unique=False, schema='behavioral_fraud')
    if not sa.inspect(bind).has_table("vacations", schema="behavioral_fraud" if pg else None):
        op.create_table('vacations',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('destination', sa.String(length=150), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('budget', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('latitude', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('longitude', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('radius_km', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_vacations_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_vacations')),
        schema='behavioral_fraud'
        )
        op.create_index(op.f('ix_behavioral_fraud_vacations_user_id'), 'vacations', ['user_id'], unique=False, schema='behavioral_fraud')
    if not sa.inspect(bind).has_table("notifications", schema="core" if pg else None):
        op.create_table('notifications',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('dedupe_key', sa.String(length=200), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.String(length=2000), nullable=False),
        sa.Column('read', sa.Boolean(), nullable=False),
        sa.Column('delivery_status', sa.String(length=30), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_notifications_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications')),
        sa.UniqueConstraint('user_id', 'dedupe_key', name=op.f('uq_notifications_user_id')),
        schema='core'
        )
        op.create_index(op.f('ix_core_notifications_user_id'), 'notifications', ['user_id'], unique=False, schema='core')
    if not sa.inspect(bind).has_table("privacy_settings", schema="core" if pg else None):
        op.create_table('privacy_settings',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('geolocation_consent', sa.Boolean(), nullable=False),
        sa.Column('home_latitude', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('home_longitude', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('radius_km', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_privacy_settings_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_privacy_settings')),
        sa.UniqueConstraint('user_id', name=op.f('uq_privacy_settings_user_id')),
        schema='core'
        )
        op.create_index(op.f('ix_core_privacy_settings_user_id'), 'privacy_settings', ['user_id'], unique=False, schema='core')
    if not sa.inspect(bind).has_table("spending_budgets", schema="core" if pg else None):
        op.create_table('spending_budgets',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('category', sa.String(length=80), nullable=False),
        sa.Column('monthly_amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_spending_budgets_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_spending_budgets')),
        sa.UniqueConstraint('user_id', 'category', name=op.f('uq_spending_budgets_user_id')),
        schema='core'
        )
        op.create_index(op.f('ix_core_spending_budgets_user_id'), 'spending_budgets', ['user_id'], unique=False, schema='core')
    if not sa.inspect(bind).has_table("forecast_snapshots", schema="predictive_planning" if pg else None):
        op.create_table('forecast_snapshots',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_forecast_snapshots_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_forecast_snapshots')),
        sa.UniqueConstraint('user_id', name=op.f('uq_forecast_snapshots_user_id')),
        schema='predictive_planning'
        )
        op.create_index(op.f('ix_predictive_planning_forecast_snapshots_user_id'), 'forecast_snapshots', ['user_id'], unique=False, schema='predictive_planning')
    if not sa.inspect(bind).has_table("scheduled_flows", schema="predictive_planning" if pg else None):
        op.create_table('scheduled_flows',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('external_id', sa.String(length=150), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=80), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('recurrence', sa.String(length=20), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('source_offer_id', base.GUID(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_scheduled_flows_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_scheduled_flows')),
        sa.UniqueConstraint('user_id', 'external_id', name=op.f('uq_scheduled_flows_user_id')),
        schema='predictive_planning'
        )
        op.create_index(op.f('ix_predictive_planning_scheduled_flows_due_date'), 'scheduled_flows', ['due_date'], unique=False, schema='predictive_planning')
        op.create_index(op.f('ix_predictive_planning_scheduled_flows_user_id'), 'scheduled_flows', ['user_id'], unique=False, schema='predictive_planning')
    if not sa.inspect(bind).has_table("shocks", schema="shock_mediation" if pg else None):
        op.create_table('shocks',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('external_id', sa.String(length=150), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('shortfall', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('routing', sa.JSON(), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_shocks_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_shocks')),
        sa.UniqueConstraint('user_id', 'external_id', name=op.f('uq_shocks_user_id')),
        schema='shock_mediation'
        )
        op.create_index(op.f('ix_shock_mediation_shocks_user_id'), 'shocks', ['user_id'], unique=False, schema='shock_mediation')
    if not sa.inspect(bind).has_table("recurring_subscriptions", schema="subscriptions" if pg else None):
        op.create_table('recurring_subscriptions',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('merchant', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=80), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('cadence', sa.String(length=20), nullable=False),
        sa.Column('next_billing', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_recurring_subscriptions_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_recurring_subscriptions')),
        sa.UniqueConstraint('user_id', 'merchant', 'cadence', name=op.f('uq_recurring_subscriptions_user_id')),
        schema='subscriptions'
        )
        op.create_index(op.f('ix_subscriptions_recurring_subscriptions_next_billing'), 'recurring_subscriptions', ['next_billing'], unique=False, schema='subscriptions')
        op.create_index(op.f('ix_subscriptions_recurring_subscriptions_user_id'), 'recurring_subscriptions', ['user_id'], unique=False, schema='subscriptions')
    if not sa.inspect(bind).has_table("installment_offers", schema="shock_mediation" if pg else None):
        op.create_table('installment_offers',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('shock_id', base.GUID(), nullable=False),
        sa.Column('months', sa.Integer(), nullable=False),
        sa.Column('terms', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('expires_on', sa.Date(), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['shock_id'], ['shock_mediation.shocks.id'], name=op.f('fk_installment_offers_shock_id_shocks')),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_installment_offers_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_installment_offers')),
        sa.UniqueConstraint('shock_id', 'months', name=op.f('uq_installment_offers_shock_id')),
        schema='shock_mediation'
        )
        op.create_index(op.f('ix_shock_mediation_installment_offers_user_id'), 'installment_offers', ['user_id'], unique=False, schema='shock_mediation')
    if not sa.inspect(bind).has_table("ledger_transactions", schema="transactions" if pg else None):
        op.create_table('ledger_transactions',
        sa.Column('id', base.GUID(), nullable=False),
        sa.Column('account_id', base.GUID(), nullable=False),
        sa.Column('external_id', sa.String(length=150), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('merchant', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=80), nullable=False),
        sa.Column('cart_size', sa.Integer(), nullable=True),
        sa.Column('latitude', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('longitude', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('vacation_id', base.GUID(), nullable=True),
        sa.Column('fraud', sa.JSON(), nullable=False),
        sa.Column('user_id', base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['core.bank_accounts.id'], name=op.f('fk_ledger_transactions_account_id_bank_accounts')),
        sa.ForeignKeyConstraint(['user_id'], ['core.users.id'], name=op.f('fk_ledger_transactions_user_id_users')),
        sa.ForeignKeyConstraint(['vacation_id'], ['behavioral_fraud.vacations.id'], name=op.f('fk_ledger_transactions_vacation_id_vacations')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ledger_transactions')),
        sa.UniqueConstraint('user_id', 'external_id', name=op.f('uq_ledger_transactions_user_id')),
        schema='transactions'
        )
        op.create_index(op.f('ix_transactions_ledger_transactions_occurred_at'), 'ledger_transactions', ['occurred_at'], unique=False, schema='transactions')
        op.create_index(op.f('ix_transactions_ledger_transactions_user_id'), 'ledger_transactions', ['user_id'], unique=False, schema='transactions')


def downgrade():
    bind = op.get_bind()
    pg = bind.dialect.name == "postgresql"
    if sa.inspect(bind).has_table("ledger_transactions", schema="transactions" if pg else None):
        op.drop_table("ledger_transactions", schema="transactions")
    if sa.inspect(bind).has_table("installment_offers", schema="shock_mediation" if pg else None):
        op.drop_table("installment_offers", schema="shock_mediation")
    if sa.inspect(bind).has_table("recurring_subscriptions", schema="subscriptions" if pg else None):
        op.drop_table("recurring_subscriptions", schema="subscriptions")
    if sa.inspect(bind).has_table("shocks", schema="shock_mediation" if pg else None):
        op.drop_table("shocks", schema="shock_mediation")
    if sa.inspect(bind).has_table("scheduled_flows", schema="predictive_planning" if pg else None):
        op.drop_table("scheduled_flows", schema="predictive_planning")
    if sa.inspect(bind).has_table("forecast_snapshots", schema="predictive_planning" if pg else None):
        op.drop_table("forecast_snapshots", schema="predictive_planning")
    if sa.inspect(bind).has_table("spending_budgets", schema="core" if pg else None):
        op.drop_table("spending_budgets", schema="core")
    if sa.inspect(bind).has_table("privacy_settings", schema="core" if pg else None):
        op.drop_table("privacy_settings", schema="core")
    if sa.inspect(bind).has_table("notifications", schema="core" if pg else None):
        op.drop_table("notifications", schema="core")
    if sa.inspect(bind).has_table("vacations", schema="behavioral_fraud" if pg else None):
        op.drop_table("vacations", schema="behavioral_fraud")
    if sa.inspect(bind).has_table("chargebacks", schema="behavioral_fraud" if pg else None):
        op.drop_table("chargebacks", schema="behavioral_fraud")
    if sa.inspect(bind).has_table("verified_summaries", schema="ai" if pg else None):
        op.drop_table("verified_summaries", schema="ai")
    if sa.inspect(bind).has_table("cpi_observations", schema="inflation" if pg else None):
        op.drop_table("cpi_observations", schema="inflation")
