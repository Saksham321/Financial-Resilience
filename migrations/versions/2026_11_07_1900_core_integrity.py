"""Bring the original core migration into alignment with existing ORM constraints."""
from alembic import op
import sqlalchemy as sa

revision = "core_integrity_v1"
down_revision = "engine_domains_v1"
branch_labels = None
depends_on = None

NAMES = ("user_profiles", "bank_accounts", "financial_goals", "user_preferences")


def upgrade():
    bind = op.get_bind()
    schema = "core" if bind.dialect.name == "postgresql" else None
    for name in NAMES:
        inspector = sa.inspect(bind)
        fks = inspector.get_foreign_keys(name, schema=schema)
        unique = inspector.get_unique_constraints(name, schema=schema)
        add_fk = not any(f["constrained_columns"] == ["user_id"] for f in fks)
        add_unique = name in ("user_profiles", "user_preferences") and not any(u["column_names"] == ["user_id"] for u in unique)
        if add_fk or add_unique:
            with op.batch_alter_table(name, schema=schema) as batch:
                if add_fk:
                    batch.create_foreign_key(f"fk_enforced_{name}_user", "users", ["user_id"], ["id"], referent_schema=schema, ondelete="CASCADE")
                if add_unique:
                    batch.create_unique_constraint(f"uq_enforced_{name}_user", ["user_id"])
        if name in ("bank_accounts", "financial_goals"):
            indexes = sa.inspect(bind).get_indexes(name, schema=schema)
            if not any(i["column_names"] == ["user_id"] for i in indexes):
                op.create_index(f"ix_core_{name}_user_id", name, ["user_id"], schema=schema)


def downgrade():
    bind = op.get_bind()
    schema = "core" if bind.dialect.name == "postgresql" else None
    for name in reversed(NAMES):
        inspector = sa.inspect(bind)
        fks = [f["name"] for f in inspector.get_foreign_keys(name, schema=schema) if f["name"] and f["name"].startswith("fk_enforced_")]
        unique = [u["name"] for u in inspector.get_unique_constraints(name, schema=schema) if u["name"] and u["name"].startswith("uq_enforced_")]
        if fks or unique:
            with op.batch_alter_table(name, schema=schema) as batch:
                for constraint in fks:
                    batch.drop_constraint(constraint, type_="foreignkey")
                for constraint in unique:
                    batch.drop_constraint(constraint, type_="unique")
