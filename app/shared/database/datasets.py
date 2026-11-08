"""Source datasets kept separate from user-owned CAD banking records."""
from datetime import datetime, timezone
from sqlalchemy import String, BigInteger, JSON, DateTime, ForeignKeyConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.shared.database.base import Base


class DatasetAccount(Base):
    __tablename__ = "source_dataset_accounts"
    __table_args__ = {"schema": "core"}
    dataset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class DatasetMonth(Base):
    __tablename__ = "source_dataset_monthly"
    __table_args__ = (ForeignKeyConstraint(
        ["dataset_id", "account_id"],
        ["core.source_dataset_accounts.dataset_id", "core.source_dataset_accounts.account_id"],
    ), {"schema": "core"})
    dataset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    month: Mapped[str] = mapped_column(String(7), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class DatasetInsights(Base):
    __tablename__ = "source_dataset_insights"
    __table_args__ = {"schema": "core"}
    dataset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    source_manifest: Mapped[dict] = mapped_column(JSON, nullable=False)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class DatasetSourceRecord(Base):
    __tablename__ = "source_dataset_records"
    __table_args__ = (Index("ix_source_records_account", "dataset_id", "account_id", "source", "period"), {"schema": "core"})
    dataset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(String(50), primary_key=True)
    record_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    account_id: Mapped[int | None] = mapped_column(BigInteger)
    period: Mapped[str | None] = mapped_column(String(10))
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class DatasetSourceFile(Base):
    __tablename__ = "source_dataset_files"
    __table_args__ = {"schema": "core"}
    dataset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    source: Mapped[str] = mapped_column(String(50), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(BigInteger)
    columns: Mapped[list] = mapped_column(JSON)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
