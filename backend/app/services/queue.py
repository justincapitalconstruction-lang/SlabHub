"""Simple in-memory queue manager.

This module provides a basic queue implementation using Python's built-in queue
module. In production, you can replace this with RQ + Redis or another
distributed queue technology. The functions here enqueue jobs and allow
worker threads to process them.
"""
from __future__ import annotations
import queue
import threading
import logging
from typing import Callable

from backend.app.models.job import Job
from backend.app.models import SessionLocal
from backend.app.crud_job import record_job_event

logger = logging.getLogger(__name__)

# Global queue for jobs
task_queue: queue.Queue[Job] = queue.Queue()


def enqueue_job(job: Job) -> None:
    """Place a job on the queue for processing."""
    task_queue.put(job)
    logger.debug(f"Enqueued job {job.id} of type {job.type}")


def worker_loop(worker_name: str, process_func: Callable[[Job], None], stop_event: threading.Event) -> None:
    """Run a worker loop that processes jobs from the queue.

    Args:
        worker_name: Identifier for the worker.
        process_func: Function that performs the job's work.
        stop_event: Event to signal when the worker should stop.
    """
    db = SessionLocal()
    while not stop_event.is_set():
        try:
            job: Job = task_queue.get(timeout=1)
        except queue.Empty:
            continue
        # Mark job as running and record event
        record_job_event(db, job, state="running", message=f"Job started by {worker_name}")
        try:
            process_func(job)
            # Record successful completion
            record_job_event(db, job, state="success", message=f"Job completed by {worker_name}")
        except Exception as e:
            logger.error(f"Error processing job {job.id}: {e}", exc_info=True)
            record_job_event(db, job, state="failed", message=str(e))
        finally:
            task_queue.task_done()
    db.close()
