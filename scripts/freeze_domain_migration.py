"""Development helper: freeze the initial domain revision before schema evolution.

Run only when intentionally regenerating engine_domains_v1 before deployment.
"""
from pathlib import Path
import textwrap
from alembic.autogenerate import render_python_code
from alembic.migration import MigrationContext
from alembic.operations.ops import UpgradeOps, CreateTableOp, CreateIndexOp
from app.shared.database.models import Base

NAMES = {"privacy_settings", "spending_budgets", "scheduled_flows", "vacations", "chargebacks", "recurring_subscriptions", "shocks", "installment_offers", "ledger_transactions", "notifications", "forecast_snapshots", "cpi_observations", "verified_summaries"}
tables = [table for table in Base.metadata.sorted_tables if table.name in NAMES]
context = MigrationContext.configure(dialect_name="postgresql")
header = '''"""Frozen financial domain schema; no runtime model imports.

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
'''
parts = [header]
for table in tables:
    operations = [CreateTableOp.from_table(table)] + [CreateIndexOp.from_index(index) for index in sorted(table.indexes, key=lambda i: i.name)]
    rendered = render_python_code(UpgradeOps(operations), migration_context=context, user_module_prefix="base.")
    body = "\n".join(line for line in rendered.splitlines() if not line.strip().startswith("#"))
    parts.append(f'    if not sa.inspect(bind).has_table("{table.name}", schema="{table.schema}" if pg else None):\n')
    parts.append(textwrap.indent(textwrap.dedent(body), "        ") + "\n")
parts.append('\n\ndef downgrade():\n    bind = op.get_bind()\n    pg = bind.dialect.name == "postgresql"\n')
for table in reversed(tables):
    parts.append(f'    if sa.inspect(bind).has_table("{table.name}", schema="{table.schema}" if pg else None):\n        op.drop_table("{table.name}", schema="{table.schema}")\n')
Path("migrations/versions/2026_11_07_1800_engine_domains.py").write_text("".join(parts), encoding="utf-8")
print(f"Froze {len(tables)} domain tables and their indexes.")
