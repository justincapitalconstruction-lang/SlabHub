"""Location model for storing physical storage locations."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from .base import Base


class Location(Base):
    """Represents a physical location where slabs can be stored."""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
