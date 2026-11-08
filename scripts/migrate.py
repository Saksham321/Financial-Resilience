"""Adopt a verified legacy create_all database, then apply versioned migrations."""
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from app.shared.database.session import sync_engine
from app.shared.database.base import Base
import app.shared.database.models  # noqa: F401


def main():
    config = Config("alembic.ini")
    inspector = inspect(sync_engine)
    schema = "core" if sync_engine.dialect.name == "postgresql" else None
    if inspector.has_table("users", schema=schema) and not inspector.has_table("alembic_version"):
        # Refuse to stamp unknown or incomplete layouts. No financial records are modified.
        for table in Base.metadata.tables.values():
            if table.schema not in ("core", "audit") or table.name in ("privacy_settings", "spending_budgets", "notifications"):
                continue
            actual_schema = table.schema if schema else None
            if not inspector.has_table(table.name, schema=actual_schema):
                raise RuntimeError(f"Legacy database is missing {table.name}; inspect before migration.")
            names = {c["name"] for c in inspector.get_columns(table.name, schema=actual_schema)}
            if not {c.name for c in table.columns} <= names:
                raise RuntimeError(f"Legacy database has an incompatible {table.name} layout.")
        command.stamp(config, "95c6cf829e7c")
    command.upgrade(config, "head")
    print("Database migrations completed.")


if __name__ == "__main__":
    main()
