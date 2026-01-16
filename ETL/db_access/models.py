"""DB models."""

from datetime import datetime
from typing import ClassVar

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy base."""


class ETLReport(Base):
    """Model containing specifications to store App data in the DB."""

    __tablename__ = "etl_reports"
    __table_args__: ClassVar[dict] = {"schema": "dbo"}

    id: Mapped[int] = mapped_column(primary_key=True)
    app_id: Mapped[int] = mapped_column(Integer)

    new_files: Mapped[int] = mapped_column(Integer)
    updated_files: Mapped[int] = mapped_column(Integer)
    deleted_files: Mapped[int] = mapped_column(Integer)
    total_files: Mapped[int] = mapped_column(Integer)
    total_chunks: Mapped[int] = mapped_column(Integer)
    files_in_db: Mapped[dict] = mapped_column(
        MutableDict.as_mutable(JSON),
    )

    date: Mapped[datetime] = mapped_column(DateTime(), server_default=func.now())