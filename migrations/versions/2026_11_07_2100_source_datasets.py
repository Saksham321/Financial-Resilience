"""Preserve processed account/monthly datasets without altering user finances."""
from alembic import op
import sqlalchemy as sa

revision = "source_datasets_v1"
down_revision = "core_integrity_v1"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    schema = "core" if bind.dialect.name == "postgresql" else None
    # Development create_all databases may already contain these tables.
    existing = set(sa.inspect(bind).get_table_names(schema=schema))
    if "source_dataset_accounts" not in existing:
        op.create_table("source_dataset_accounts",
            sa.Column("dataset_id", sa.String(100), primary_key=True),
            sa.Column("account_id", sa.BigInteger(), primary_key=True),
            sa.Column("payload", sa.JSON(), nullable=False), schema=schema)
    if "source_dataset_monthly" not in existing:
        parent = f"{schema}." if schema else ""
        op.create_table("source_dataset_monthly",
            sa.Column("dataset_id", sa.String(100), primary_key=True),
            sa.Column("account_id", sa.BigInteger(), primary_key=True),
            sa.Column("month", sa.String(7), primary_key=True),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.ForeignKeyConstraint(["dataset_id", "account_id"],
                [parent + "source_dataset_accounts.dataset_id", parent + "source_dataset_accounts.account_id"]), schema=schema)
    if "source_dataset_insights" not in existing:
        op.create_table("source_dataset_insights",
            sa.Column("dataset_id", sa.String(100), primary_key=True),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("source_manifest", sa.JSON(), nullable=False),
            sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False), schema=schema)


def downgrade():
    schema = "core" if op.get_bind().dialect.name == "postgresql" else None
    for name in ("source_dataset_insights", "source_dataset_monthly", "source_dataset_accounts"):
        op.drop_table(name, schema=schema)
