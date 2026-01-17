"""Catalog loading and AI candidate retrieval service.

This module provides functions to load a catalog of slab characteristics and
retrieve candidate entries for AI analysis. It also defines Stage‑1 and
Stage‑2 prompts used for GPT-based classification and extraction. The actual
catalog data lives in JSON files under backend/app/gpt/catalog.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict, List

from backend.app.services.gpt_client import GPTClient
from backend.app.models import SessionLocal
from backend.app.models.gpt import GPTRequest, GPTResponse

CATALOG_DIR = Path(__file__).resolve().parent.parent / "gpt" / "catalog"
INDEX_PATH = CATALOG_DIR / "index.json"
FULL_PATH = CATALOG_DIR / "full.json"


def load_index() -> List[Dict[str, Any]]:
    """Load the catalog index JSON file."""
    if not INDEX_PATH.exists():
        return []
    return json.loads(INDEX_PATH.read_text())


def load_full_catalog() -> List[Dict[str, Any]]:
    """Load the full catalog JSON file."""
    if not FULL_PATH.exists():
        return []
    return json.loads(FULL_PATH.read_text())


def stage1_prompt(slug: str, limit: int = 20) -> str:
    """Generate a Stage‑1 candidate prompt for retrieving catalog candidates.

    Args:
        slug: The field to classify (e.g., "stone_type").
        limit: Maximum number of candidates to return.

    Returns:
        A prompt string.
    """
    return (
        f"Given a stone slab description, list up to {limit} candidate {slug} values from the catalog. "
        "Return only the candidates separated by commas."
    )


def stage2_prompt(slug: str) -> str:
    """Generate a Stage‑2 extraction prompt.

    Args:
        slug: The field to extract (e.g., "color", "veins").

    Returns:
        A prompt string instructing the model to extract details with confidence scores.
    """
    return (
        f"From the candidate {slug} list, select the most likely value and "
        "provide a confidence score between 0 and 1."
    )


def classify_slab_field(prompt: str, field: str, slab_description: str) -> Dict[str, Any]:
    """Perform Stage‑1 and Stage‑2 classification for a single slab field.

    This function uses the GPTClient to send prompts and stores the requests
    and responses in the database.

    Args:
        prompt: The Stage‑1 prompt to generate candidates.
        field: Name of the field being classified.
        slab_description: Description of the slab provided by the user.

    Returns:
        A dictionary containing candidates, selected value and confidence score.
    """
    db = SessionLocal()
    client = GPTClient()
    # Stage 1: candidate retrieval
    req1 = GPTRequest(prompt=f"{prompt}\nDescription: {slab_description}")
    db.add(req1)
    db.commit()
    db.refresh(req1)
    result1 = client.send_prompt(req1.prompt)
    resp1 = GPTResponse(
        request_id=req1.id,
        raw_response=result1["raw"],
        parsed_response=result1["parsed"],
        tokens=result1.get("tokens"),
        latency_ms=result1.get("latency_ms"),
    )
    db.add(resp1)
    db.commit()
    candidates = [c.strip() for c in result1["parsed"].split(",") if c.strip()]
    # Stage 2: extraction
    stage2 = stage2_prompt(field)
    req2 = GPTRequest(prompt=f"{stage2}\nCandidates: {', '.join(candidates)}\nDescription: {slab_description}")
    db.add(req2)
    db.commit()
    db.refresh(req2)
    result2 = client.send_prompt(req2.prompt)
    resp2 = GPTResponse(
        request_id=req2.id,
        raw_response=result2["raw"],
        parsed_response=result2["parsed"],
        tokens=result2.get("tokens"),
        latency_ms=result2.get("latency_ms"),
    )
    db.add(resp2)
    db.commit()
    db.close()
    # Parse Stage‑2 result: expected format "value:confidence"
    parts = result2["parsed"].split(":")
    value = parts[0].strip() if parts else None
    confidence = float(parts[1]) if len(parts) > 1 else None
    return {
        "candidates": candidates,
        "value": value,
        "confidence": confidence,
    }
