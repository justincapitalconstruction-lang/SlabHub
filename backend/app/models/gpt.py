"""Models for storing GPT request and response data."""
from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey

from .base import Base


class GPTRequest(Base):
    """Represents a request sent to a GPT model."""
    __tablename__ = "gpt_requests"

    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GPTResponse(Base):
    """Stores a response from a GPT model along with metrics."""
    __tablename__ = "gpt_responses"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("gpt_requests.id"), nullable=False)
    raw_response = Column(Text, nullable=True)
    parsed_response = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
