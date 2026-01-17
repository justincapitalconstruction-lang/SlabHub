"""AnalysisResult model for storing AI analysis outcomes for slabs."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey

from .base import Base


class AnalysisResult(Base):
    """Stores AI analysis results for a slab field."""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    slab_id = Column(Integer, ForeignKey("slabs.id"), nullable=False)
    field = Column(String(100), nullable=False)
    value = Column(String(255), nullable=True)
    confidence = Column(Numeric, nullable=True)
    raw_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
