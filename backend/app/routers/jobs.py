"""API routes for job management."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.models import get_db
from backend.app.crud_job import create_job, get_job, list_jobs, get_job_events


class JobCreate(BaseModel):
    type: str
    payload: str | None = None
    idempotency_key: str | None = None


class JobOut(BaseModel):
    id: int
    type: str
    state: str
    payload: str | None
    result: str | None
    error: str | None
    attempts: int
    lease_owner: str | None
    lease_expires_at: str | None
    idempotency_key: str | None
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True


class JobEventOut(BaseModel):
    id: int
    job_id: int
    state: str
    message: str | None
    created_at: str

    class Config:
        orm_mode = True


router = APIRouter()


@router.post("", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def submit_job(job_data: JobCreate, db: Session = Depends(get_db)):
    """Create a new job."""
    job = create_job(db, type=job_data.type, payload=job_data.payload, idempotency_key=job_data.idempotency_key)
    return job


@router.get("", response_model=List[JobOut])
def get_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List jobs."""
    jobs = list_jobs(db, skip=skip, limit=limit)
    return jobs


@router.get("/{job_id}", response_model=JobOut)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)):
    """Retrieve a job by ID."""
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/{job_id}/events", response_model=List[JobEventOut])
def get_events_for_job(job_id: int, db: Session = Depends(get_db)):
    """Retrieve job events."""
    job = get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    events = get_job_events(db, job_id)
    return events
