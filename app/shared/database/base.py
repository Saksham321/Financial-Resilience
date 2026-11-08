"""
Database Base Class & Entity Mixins
SQLAlchemy 2.0 Declarative Base with UUIDs and UTC Timestamps
"""

import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import MetaData, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, CHAR

class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(str(value)))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(str(value))
            return value

# Standardized constraint naming conventions for repeatable migrations
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata_obj = MetaData(naming_convention=convention)

class Base(DeclarativeBase):
    metadata = metadata_obj

class UUIDPrimaryKeyMixin:
    """Mixin for UUID primary keys."""
    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-100,
        doc="Unique Entity UUID identifier"
    )

class TimestampMixin:
    """Mixin for timezone-aware audit timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        sort_order=100,
        doc="Timestamp of creation (UTC)"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        sort_order=101,
        doc="Timestamp of last modification (UTC)"
    )
