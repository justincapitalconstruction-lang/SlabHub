"""API routes for invoking GPT analysis."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.models import get_db
from backend.app.models.gpt import GPTRequest, GPTResponse
from backend.app.services.gpt_client import GPTClient

router = APIRouter()


class GPTPrompt(BaseModel):
    prompt: str


@router.post("", status_code=status.HTTP_201_CREATED)
def run_gpt(prompt_data: GPTPrompt, db: Session = Depends(get_db)):
    """Submit a prompt to the GPT service and store the result."""
    # Create a request record
    req = GPTRequest(prompt=prompt_data.prompt)
    db.add(req)
    db.commit()
    db.refresh(req)
    # Use client to send prompt
    client = GPTClient()
    try:
        result = client.send_prompt(prompt_data.prompt)
        resp = GPTResponse(
            request_id=req.id,
            raw_response=result["raw"],
            parsed_response=result["parsed"],
            tokens=result.get("tokens"),
            latency_ms=result.get("latency_ms"),
        )
        db.add(resp)
        db.commit()
        return {
            "request_id": req.id,
            "response_id": resp.id,
            "content": result["parsed"],
            "tokens": result.get("tokens"),
            "latency_ms": result.get("latency_ms"),
        }
    except Exception as e:
        # Persist error
        resp = GPTResponse(request_id=req.id, error=str(e))
        db.add(resp)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
