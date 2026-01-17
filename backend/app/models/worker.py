"""Worker model for queue system."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime

from .base import Base


class Worker(Base):
    """Represents a worker process for the job queue."""
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    heartbeat_at = Column(DateTime, default=datetime.utcnow)
