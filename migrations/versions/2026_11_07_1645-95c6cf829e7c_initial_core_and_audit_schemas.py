"""initial_core_and_audit_schemas

Revision ID: 95c6cf829e7c
Revises: 
Create Date: 2026-11-07 16:45:14.710298

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '95c6cf829e7c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create Logical Schemas if PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE SCHEMA IF NOT EXISTS core;")
        op.execute("CREATE SCHEMA IF NOT EXISTS audit;")

    # 2. Users Table
    op.create_table(
        'users',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='user'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_users'),
        schema='core' if bind.dialect.name == "postgresql" else None
    )
    op.create_index('ix_core_users_email', 'users', ['email'], unique=True, schema='core' if bind.dialect.name == "postgresql" else None)

    # 3. User Profiles Table
    op.create_table(
        'user_profiles',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=30), nullable=True),
        sa.Column('birth_date', sa.Date(), nullable=True),
        sa.Column('risk_tier', sa.String(length=30), nullable=False, server_default='MODERATE'),
        sa.Column('annual_income', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('credit_score_estimate', sa.Integer(), nullable=True),
        sa.Column('province', sa.String(length=50), nullable=False, server_default='Ontario'),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_user_profiles'),
        schema='core' if bind.dialect.name == "postgresql" else None
    )

    # 4. Bank Accounts Table
    op.create_table(
        'bank_accounts',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('institution_name', sa.String(length=100), nullable=False),
        sa.Column('account_type', sa.String(length=50), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='CAD'),
        sa.Column('masked_account_number', sa.String(length=20), nullable=False),
        sa.Column('current_balance', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('available_balance', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_bank_accounts'),
        schema='core' if bind.dialect.name == "postgresql" else None
    )

    # 5. Financial Goals Table
    op.create_table(
        'financial_goals',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('target_amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('current_amount', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_financial_goals'),
        schema='core' if bind.dialect.name == "postgresql" else None
    )

    # 6. User Preferences Table
    op.create_table(
        'user_preferences',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('consent_ai_processing', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('consent_browsing_context', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('notification_channel', sa.String(length=30), nullable=False, server_default='EMAIL'),
        sa.Column('vacation_mode_active', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_user_preferences'),
        schema='core' if bind.dialect.name == "postgresql" else None
    )

    # 7. Audit System Events Table
    op.create_table(
        'system_events',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('correlation_id', sa.String(length=100), nullable=True),
        sa.Column('details', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_system_events'),
        schema='audit' if bind.dialect.name == "postgresql" else None
    )

    # 8. Financial Decisions Audit Table
    op.create_table(
        'financial_decisions',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('decision_type', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('inputs', sa.JSON(), nullable=False),
        sa.Column('outputs', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_financial_decisions'),
        schema='audit' if bind.dialect.name == "postgresql" else None
    )

    # 9. User Consents Table
    op.create_table(
        'user_consents',
        sa.Column('id', sa.CHAR(36), nullable=False),
        sa.Column('user_id', sa.CHAR(36), nullable=False),
        sa.Column('consent_type', sa.String(length=100), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('terms_version', sa.String(length=20), nullable=False, server_default='1.0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pk_user_consents'),
        schema='audit' if bind.dialect.name == "postgresql" else None
    )

def downgrade() -> None:
    bind = op.get_bind()
    op.drop_table('user_consents', schema='audit' if bind.dialect.name == "postgresql" else None)
    op.drop_table('financial_decisions', schema='audit' if bind.dialect.name == "postgresql" else None)
    op.drop_table('system_events', schema='audit' if bind.dialect.name == "postgresql" else None)
    op.drop_table('user_preferences', schema='core' if bind.dialect.name == "postgresql" else None)
    op.drop_table('financial_goals', schema='core' if bind.dialect.name == "postgresql" else None)
    op.drop_table('bank_accounts', schema='core' if bind.dialect.name == "postgresql" else None)
    op.drop_table('user_profiles', schema='core' if bind.dialect.name == "postgresql" else None)
    op.drop_table('users', schema='core' if bind.dialect.name == "postgresql" else None)
