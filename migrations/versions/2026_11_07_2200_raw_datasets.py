"""Retain the supplied CSV source records and per-file import manifests."""
from alembic import op
import sqlalchemy as sa

revision = "raw_datasets_v1"
down_revision = "source_datasets_v1"
branch_labels = None
depends_on = None


def upgrade():
    schema = "core" if op.get_bind().dialect.name == "postgresql" else None
    existing = set(sa.inspect(op.get_bind()).get_table_names(schema=schema))
    if "source_dataset_records" not in existing:
        op.create_table("source_dataset_records",
            sa.Column("dataset_id", sa.String(100), primary_key=True),
            sa.Column("source", sa.String(50), primary_key=True),
            sa.Column("record_key", sa.String(100), primary_key=True),
            sa.Column("account_id", sa.BigInteger()), sa.Column("period", sa.String(10)),
            sa.Column("payload", sa.JSON(), nullable=False), schema=schema)
        op.create_index("ix_source_records_account", "source_dataset_records", ["dataset_id", "account_id", "source", "period"], schema=schema)
    if "source_dataset_files" not in existing:
        op.create_table("source_dataset_files",
            sa.Column("dataset_id", sa.String(100), primary_key=True),
            sa.Column("source", sa.String(50), primary_key=True),
            sa.Column("sha256", sa.String(64), nullable=False),
            sa.Column("row_count", sa.BigInteger(), nullable=False),
            sa.Column("columns", sa.JSON(), nullable=False),
            sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False), schema=schema)


def downgrade():
    schema = "core" if op.get_bind().dialect.name == "postgresql" else None
    op.drop_table("source_dataset_files", schema=schema)
    op.drop_table("source_dataset_records", schema=schema)
