"""
SlabHub Database Models
Exports all SQLAlchemy models for the inventory system
"""
from backend.app.models.base import Base, engine, SessionLocal, get_db, init_db
from backend.app.models.slab import Slab
from backend.app.models.inventory import InventoryItem, Shipment
from backend.app.models.import_log import ImportLog
from backend.app.models.job import Job, JobEvent
from backend.app.models.worker import Worker
from backend.app.models.gpt import GPTRequest, GPTResponse

# Export all models and utilities
__all__ = [
    # Base database utilities
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",

    # Models
    "Slab",
    "InventoryItem",
    "Shipment",
    "ImportLog",
    "Job",
    "JobEvent",
    "Worker",
    "GPTRequest",
    "GPTResponse",
]
