"""Job and JobEvent models for SlabHub."""
from __future__ import annotations
import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class JobState(str, enum.Enum):
    """Enumeration of possible job states."""
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"
    canceled = "canceled"
    timeout = "timeout"


class Job(Base):
    """Represents a unit of work processed by the worker system."""
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)
    state = Column(String, nullable=False, default=JobState.pending.value)
    payload = Column(Text, nullable=True)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    attempts = Column(Integer, default=0)
    lease_owner = Column(String, nullable=True)
    lease_expires_at = Column(DateTime, nullable=True)
    idempotency_key = Column(String, nullable=True, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    events = relationship("JobEvent", back_populates="job")


class JobEvent(Base):
    """Records state transitions and events for a job."""
    __tablename__ = "job_events"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    state = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="events")
