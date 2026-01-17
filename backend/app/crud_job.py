"""CRUD operations for Job and JobEvent."""
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.app.models.job import Job, JobEvent


def create_job(db: Session, *, type: str, payload: str = None, idempotency_key: str = None) -> Job:
    """Create a new job and record an initial event."""
    job = Job(type=type, payload=payload, idempotency_key=idempotency_key)
    db.add(job)
    db.commit()
    db.refresh(job)
    # Record initial event
    event = JobEvent(job_id=job.id, state=job.state, message="Job created")
    db.add(event)
    db.commit()
    return job


def get_job(db: Session, job_id: int) -> Optional[Job]:
    """Fetch a job by its ID."""
    return db.query(Job).filter(Job.id == job_id).first()


def list_jobs(db: Session, *, skip: int = 0, limit: int = 100) -> List[Job]:
    """List jobs with pagination."""
    return db.query(Job).offset(skip).limit(limit).all()


def record_job_event(db: Session, job: Job, state: str, message: str = None) -> JobEvent:
    """Record a job event and update the job state."""
    job.state = state
    db.add(job)
    event = JobEvent(job_id=job.id, state=state, message=message)
    db.add(event)
    db.commit()
    db.refresh(job)
    return event


def get_job_events(db: Session, job_id: int) -> List[JobEvent]:
    """Return the list of events for a job."""
    return db.query(JobEvent).filter(JobEvent.job_id == job_id).order_by(JobEvent.created_at.asc()).all()
