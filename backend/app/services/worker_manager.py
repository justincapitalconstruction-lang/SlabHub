"""Worker manager to start and stop background worker threads."""
from __future__ import annotations
import threading
import logging

from backend.app.services.queue import worker_loop
from backend.app.models.worker import Worker
from backend.app.models import SessionLocal
from backend.app.version import __version__

logger = logging.getLogger(__name__)

_stop_event = threading.Event()
_worker_thread: threading.Thread | None = None


def start_worker(process_func) -> None:
    """Start a background worker thread if not already running."""
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        logger.warning("Worker already running")
        return
    # Register worker in database
    db = SessionLocal()
    worker = Worker(name="worker-1", version=__version__)
    db.add(worker)
    db.commit()
    db.refresh(worker)
    db.close()
    # Start worker thread
    _worker_thread = threading.Thread(target=worker_loop, args=(worker.name, process_func, _stop_event), daemon=True)
    _worker_thread.start()
    logger.info(f"Started worker {worker.name}")


def stop_worker() -> None:
    """Signal the worker thread to stop and wait for it to finish."""
    _stop_event.set()
    if _worker_thread:
        _worker_thread.join()
        logger.info("Worker stopped")
