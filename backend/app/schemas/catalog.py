"""Pydantic schemas for catalog responses."""
from typing import List, Optional
from pydantic import BaseModel


class CatalogItem(BaseModel):
    value: str
    confidence: Optional[float]


class CatalogResponse(BaseModel):
    candidates: List[str]
    value: Optional[str]
    confidence: Optional[float]
