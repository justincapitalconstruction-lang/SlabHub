"""AuditLog model for recording changes to database rows."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime

from .base import Base


class AuditLog(Base):
    """Record of insert/update/delete actions on database tables."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)
    row_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)  # e.g. insert, update, delete
    diff = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
