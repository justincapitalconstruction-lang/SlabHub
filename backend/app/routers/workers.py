"""API routes for monitoring workers."""
from fastapi import APIRouter
from backend.app.models import SessionLocal
from backend.app.models.worker import Worker

router = APIRouter()


@router.get("", summary="List registered workers")
def list_workers():
    """Return registered workers and their heartbeat timestamps."""
    db = SessionLocal()
    workers = db.query(Worker).all()
    db.close()
    return {
        "workers": [
            {
                "id": w.id,
                "name": w.name,
                "version": w.version,
                "created_at": w.created_at.isoformat() if w.created_at else None,
                "heartbeat_at": w.heartbeat_at.isoformat() if w.heartbeat_at else None,
            }
            for w in workers
        ]
    }
