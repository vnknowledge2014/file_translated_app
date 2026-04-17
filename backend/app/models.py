"""SQLAlchemy ORM models for the JP→VI translation tool."""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    ForeignKey,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


class Job(Base):
    """Translation job tracking."""
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    output_path = Column(String, nullable=True)
    status = Column(String, nullable=False, default="pending")
    progress = Column(Float, nullable=False, default=0.0)
    progress_message = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    segments_count = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    attempts = relationship("JobAttempt", back_populates="job", cascade="all, delete-orphan")


class JobAttempt(Base):
    """Debug trail for retry analysis."""
    __tablename__ = "job_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    phase = Column(String, nullable=False)
    code_generated = Column(Text, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    job = relationship("Job", back_populates="attempts")


class GlossaryTerm(Base):
    """User-defined translation glossary."""
    __tablename__ = "glossary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jp = Column(String, nullable=False, unique=True)
    vi = Column(String, nullable=False)
    context = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
