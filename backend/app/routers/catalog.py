"""API routes for catalog classification and extraction."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.services.catalog import stage1_prompt, classify_slab_field
from backend.app.models import get_db
from backend.app.schemas.catalog import CatalogResponse

router = APIRouter()


class CatalogQuery(BaseModel):
    field: str
    description: str
    limit: int = 10


@router.post("", response_model=CatalogResponse)
def classify_catalog(query: CatalogQuery, db: Session = Depends(get_db)):
    """Classify a slab description for a given field using catalog prompts."""
    try:
        prompt = stage1_prompt(query.field, limit=query.limit)
        result = classify_slab_field(prompt, query.field, query.description)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
