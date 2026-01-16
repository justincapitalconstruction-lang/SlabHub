#!/usr/bin/env python3
"""
Worker Manager for SlabHub - Phase 4 Queue & Workers

Provides worker lifecycle management including:
- Starting and stopping workers
- Health monitoring and heartbeat checking
- Automatic restart of dead workers
- Graceful shutdown handling

Usage:
    python worker_manager.py start --count 4 --type default
    python worker_manager.py stop
    python worker_manager.py status
    python worker_manager.py restart-dead
"""

import os
import sys
import time
import signal
import socket
import uuid
import logging
import argparse
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any

# Add parent directory to path for imports
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.app.models import SessionLocal, Worker
from backend.app.models.worker import WorkerStatus
from backend.app.config import get_version

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Worker process tracking
_active_workers: Dict[str, subprocess.Popen] = {}
_shutdown_requested = False
_monitor_thread: Optional[threading.Thread] = None


class WorkerManager:
    """
    Manages worker processes for job processing.

    Handles worker lifecycle, health monitoring, and automatic recovery.
    """

    def __init__(self):
        """Initialize worker manager"""
        self.hostname = socket.gethostname()
        self.db = SessionLocal()
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 90  # seconds - worker considered dead after this
        self.restart_delay = 5  # seconds before restarting dead worker

    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()

    # =========================================================================
    # Worker Registration
    # =========================================================================

    def register_worker(
        self,
        worker_type: str = "default",
        queues: Optional[List[str]] = None,
        concurrency: int = 1
    ) -> Worker:
        """
        Register a new worker in the database.

        Args:
            worker_type: Type of worker (default, gpt, import, etc.)
            queues: List of queues this worker processes
            concurrency: Number of concurrent jobs

        Returns:
            Registered Worker instance
        """
        worker_id = f"{self.hostname}-{os.getpid()}-{uuid.uuid4().hex[:8]}"

        worker = Worker(
            worker_id=worker_id,
            hostname=self.hostname,
            pid=os.getpid(),
            worker_type=worker_type,
            queues=queues,
            concurrency=concurrency,
            app_version=get_version(),
            status=WorkerStatus.STARTING,
            last_heartbeat_at=datetime.utcnow()
        )

        self.db.add(worker)
        self.db.commit()
        self.db.refresh(worker)

        logger.info(f"Registered worker: {worker_id} (type={worker_type})")
        return worker

    def unregister_worker(self, worker_id: str) -> bool:
        """
        Unregister a worker (mark as stopped).

        Args:
            worker_id: Worker ID to unregister

        Returns:
            True if successfully unregistered
        """
        worker = self.db.query(Worker).filter(
            Worker.worker_id == worker_id
        ).first()

        if not worker:
            logger.warning(f"Worker {worker_id} not found for unregistration")
            return False

        worker.status = WorkerStatus.STOPPED
        worker.stopped_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Unregistered worker: {worker_id}")
        return True

    def update_heartbeat(self, worker_id: str, current_job_id: Optional[str] = None) -> bool:
        """
        Update worker heartbeat.

        Args:
            worker_id: Worker ID
            current_job_id: Currently processing job ID (if any)

        Returns:
            True if heartbeat updated successfully
        """
        worker = self.db.query(Worker).filter(
            Worker.worker_id == worker_id
        ).first()

        if not worker:
            return False

        worker.last_heartbeat_at = datetime.utcnow()
        worker.current_job_id = current_job_id

        if current_job_id:
            worker.status = WorkerStatus.BUSY
        else:
            worker.status = WorkerStatus.IDLE

        self.db.commit()
        return True

    # =========================================================================
    # Worker Lifecycle
    # =========================================================================

    def start_workers(
        self,
        count: int = 1,
        worker_type: str = "default",
        queues: Optional[List[str]] = None
    ) -> List[str]:
        """
        Start multiple worker processes.

        Args:
            count: Number of workers to start
            worker_type: Type of workers to start
            queues: Optional list of queues for workers to process

        Returns:
            List of started worker IDs
        """
        global _active_workers

        started = []
        worker_script = project_root / "scripts" / "worker_process.py"

        # Create worker_process.py if it doesn't exist
        if not worker_script.exists():
            self._create_worker_process_script(worker_script)

        for i in range(count):
            try:
                # Build command
                cmd = [
                    sys.executable,
                    str(worker_script),
                    "--type", worker_type
                ]

                if queues:
                    cmd.extend(["--queues", ",".join(queues)])

                # Start process
                logger.info(f"Starting worker {i+1}/{count} (type={worker_type})")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(project_root)
                )

                # Generate a temporary ID until worker registers itself
                temp_id = f"starting-{uuid.uuid4().hex[:8]}"
                _active_workers[temp_id] = process
                started.append(temp_id)

                # Brief delay between starts
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Failed to start worker: {e}")

        logger.info(f"Started {len(started)} workers")
        return started

    def stop_all_workers(self, graceful: bool = True, timeout: int = 30) -> int:
        """
        Stop all workers managed by this manager.

        Args:
            graceful: If True, request graceful shutdown
            timeout: Seconds to wait for graceful shutdown

        Returns:
            Number of workers stopped
        """
        global _active_workers, _shutdown_requested

        _shutdown_requested = True
        stopped = 0

        # Request graceful shutdown for all workers in database
        if graceful:
            workers = self.db.query(Worker).filter(
                Worker.status.in_([WorkerStatus.IDLE, WorkerStatus.BUSY]),
                Worker.hostname == self.hostname
            ).all()

            for worker in workers:
                worker.shutdown_requested = True
                worker.shutdown_reason = "Manager shutdown"
            self.db.commit()

            logger.info(f"Requested graceful shutdown for {len(workers)} workers")

            # Wait for graceful shutdown
            deadline = time.time() + timeout
            while time.time() < deadline:
                active = self.db.query(Worker).filter(
                    Worker.status.in_([WorkerStatus.IDLE, WorkerStatus.BUSY]),
                    Worker.hostname == self.hostname
                ).count()

                if active == 0:
                    break

                time.sleep(1)

        # Force stop any remaining processes
        for worker_id, process in list(_active_workers.items()):
            try:
                if process.poll() is None:  # Still running
                    logger.warning(f"Force stopping worker {worker_id}")
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                stopped += 1
            except Exception as e:
                logger.error(f"Error stopping worker {worker_id}: {e}")

        _active_workers.clear()

        # Mark all local workers as stopped
        self.db.query(Worker).filter(
            Worker.hostname == self.hostname,
            Worker.status.in_([WorkerStatus.IDLE, WorkerStatus.BUSY, WorkerStatus.STARTING])
        ).update(
            {"status": WorkerStatus.STOPPED, "stopped_at": datetime.utcnow()},
            synchronize_session=False
        )
        self.db.commit()

        logger.info(f"Stopped {stopped} workers")
        return stopped

    # =========================================================================
    # Health Monitoring
    # =========================================================================

    def check_worker_health(self) -> Dict[str, Any]:
        """
        Check health of all workers.

        Returns:
            Health status including alive, dead, and stale workers
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.heartbeat_timeout)

        # Get all workers
        all_workers = self.db.query(Worker).filter(
            Worker.status.in_([
                WorkerStatus.IDLE,
                WorkerStatus.BUSY,
                WorkerStatus.STARTING
            ])
        ).all()

        alive = []
        dead = []
        stale = []

        for worker in all_workers:
            if worker.last_heartbeat_at and worker.last_heartbeat_at > cutoff:
                alive.append(worker.worker_id)
            elif worker.last_heartbeat_at:
                # Heartbeat expired
                dead.append(worker.worker_id)
            else:
                stale.append(worker.worker_id)

        return {
            "total": len(all_workers),
            "alive": len(alive),
            "dead": len(dead),
            "stale": len(stale),
            "alive_workers": alive,
            "dead_workers": dead,
            "stale_workers": stale,
            "checked_at": now.isoformat()
        }

    def mark_dead_workers(self) -> int:
        """
        Mark workers with expired heartbeats as dead.

        Returns:
            Number of workers marked as dead
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.heartbeat_timeout)

        # Find and mark dead workers
        dead_workers = self.db.query(Worker).filter(
            Worker.status.in_([WorkerStatus.IDLE, WorkerStatus.BUSY]),
            Worker.last_heartbeat_at < cutoff
        ).all()

        for worker in dead_workers:
            logger.warning(f"Marking worker {worker.worker_id} as dead (no heartbeat)")
            worker.status = WorkerStatus.DEAD

        self.db.commit()

        return len(dead_workers)

    def restart_dead_workers(self) -> int:
        """
        Restart workers that have died.

        Returns:
            Number of workers restarted
        """
        # First mark any workers with expired heartbeats as dead
        self.mark_dead_workers()

        # Get dead workers from this host
        dead_workers = self.db.query(Worker).filter(
            Worker.status == WorkerStatus.DEAD,
            Worker.hostname == self.hostname
        ).all()

        restarted = 0
        for worker in dead_workers:
            try:
                logger.info(f"Restarting dead worker: {worker.worker_id}")

                # Start replacement worker
                started = self.start_workers(
                    count=1,
                    worker_type=worker.worker_type,
                    queues=worker.queues
                )

                if started:
                    # Mark old worker as fully stopped
                    worker.status = WorkerStatus.STOPPED
                    worker.stopped_at = datetime.utcnow()
                    worker.shutdown_reason = "Replaced by restart"
                    restarted += 1

                time.sleep(self.restart_delay)

            except Exception as e:
                logger.error(f"Failed to restart worker {worker.worker_id}: {e}")

        self.db.commit()
        return restarted

    def get_worker_status(self) -> List[Dict[str, Any]]:
        """
        Get status of all workers.

        Returns:
            List of worker status dictionaries
        """
        workers = self.db.query(Worker).order_by(
            Worker.status,
            Worker.started_at.desc()
        ).all()

        return [worker.to_dict() for worker in workers]

    # =========================================================================
    # Monitoring Loop
    # =========================================================================

    def start_monitoring(self, interval: int = 30):
        """
        Start background monitoring thread.

        Args:
            interval: Seconds between health checks
        """
        global _monitor_thread, _shutdown_requested

        def monitor_loop():
            while not _shutdown_requested:
                try:
                    # Check for dead workers
                    dead_count = self.mark_dead_workers()
                    if dead_count > 0:
                        logger.warning(f"Found {dead_count} dead workers")

                    # Restart dead workers (if configured)
                    # self.restart_dead_workers()

                except Exception as e:
                    logger.error(f"Error in monitor loop: {e}")

                # Sleep in small increments to allow quick shutdown
                for _ in range(interval):
                    if _shutdown_requested:
                        break
                    time.sleep(1)

        _monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        _monitor_thread.start()
        logger.info("Started worker monitoring thread")

    def stop_monitoring(self):
        """Stop the monitoring thread"""
        global _shutdown_requested, _monitor_thread

        _shutdown_requested = True
        if _monitor_thread and _monitor_thread.is_alive():
            _monitor_thread.join(timeout=5)
        logger.info("Stopped worker monitoring thread")

    # =========================================================================
    # Worker Process Script
    # =========================================================================

    def _create_worker_process_script(self, script_path: Path):
        """
        Create the worker process script if it doesn't exist.

        Args:
            script_path: Path to create the script at
        """
        script_content = '''#!/usr/bin/env python3
"""
Worker Process for SlabHub - Phase 4 Queue & Workers

This script runs as a worker process, processing jobs from queues.
Managed by worker_manager.py.
"""

import os
import sys
import time
import signal
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.app.models import SessionLocal, Job
from backend.app.models.job import JobStatus
from backend.app.services.job_service import JobService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkerProcess:
    """Individual worker process that processes jobs"""

    def __init__(self, worker_type: str = "default", queues: list = None):
        self.worker_type = worker_type
        self.queues = queues or ["default"]
        self.shutdown_requested = False
        self.current_job = None

        # Set up signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        logger.info(f"Received shutdown signal {signum}")
        self.shutdown_requested = True

    def run(self):
        """Main worker loop"""
        logger.info(f"Worker starting (type={self.worker_type}, queues={self.queues})")

        from scripts.worker_manager import WorkerManager
        manager = WorkerManager()

        # Register worker
        worker = manager.register_worker(
            worker_type=self.worker_type,
            queues=self.queues
        )
        worker_id = worker.worker_id

        try:
            job_service = JobService()

            while not self.shutdown_requested:
                # Update heartbeat
                manager.update_heartbeat(worker_id, None)

                # Try to acquire a job
                job = job_service.acquire_pending_job(
                    worker_id=worker_id,
                    job_types=None  # Process all job types
                )

                if job:
                    self.current_job = job
                    manager.update_heartbeat(worker_id, job.job_id)

                    try:
                        logger.info(f"Processing job {job.job_id} (type={job.job_type})")
                        self._process_job(job, job_service)
                    except Exception as e:
                        logger.error(f"Job {job.job_id} failed: {e}")
                        job_service.fail_job(job, str(e))
                    finally:
                        self.current_job = None
                else:
                    # No jobs available, wait a bit
                    time.sleep(1)

        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            # Unregister worker
            manager.unregister_worker(worker_id)
            manager.close()
            logger.info(f"Worker {worker_id} stopped")

    def _process_job(self, job: Job, job_service: JobService):
        """Process a single job"""
        # Update progress
        job_service.update_progress(job, 0, "Starting job")

        # TODO: Add actual job processing logic based on job_type
        # For now, simulate work
        for i in range(5):
            if self.shutdown_requested:
                logger.info(f"Shutdown requested, stopping job {job.job_id}")
                return

            time.sleep(0.5)
            job_service.update_progress(job, (i + 1) * 20, f"Processing step {i + 1}/5")

        # Complete job
        job_service.complete_job(job, {"result": "success"})
        logger.info(f"Completed job {job.job_id}")


def main():
    parser = argparse.ArgumentParser(description="SlabHub Worker Process")
    parser.add_argument("--type", default="default", help="Worker type")
    parser.add_argument("--queues", default="default", help="Comma-separated list of queues")
    args = parser.parse_args()

    queues = [q.strip() for q in args.queues.split(",")]
    worker = WorkerProcess(worker_type=args.type, queues=queues)
    worker.run()


if __name__ == "__main__":
    main()
'''
        script_path.write_text(script_content)
        logger.info(f"Created worker process script: {script_path}")


# ============================================================================
# CLI Entry Points
# ============================================================================

def cmd_start(args):
    """Start workers command"""
    manager = WorkerManager()
    try:
        queues = args.queues.split(",") if args.queues else None
        started = manager.start_workers(
            count=args.count,
            worker_type=args.type,
            queues=queues
        )
        print(f"Started {len(started)} workers")

        if args.monitor:
            manager.start_monitoring()
            print("Monitoring workers... Press Ctrl+C to stop")

            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass

            manager.stop_monitoring()
            manager.stop_all_workers()

    finally:
        manager.close()


def cmd_stop(args):
    """Stop workers command"""
    manager = WorkerManager()
    try:
        stopped = manager.stop_all_workers(
            graceful=not args.force,
            timeout=args.timeout
        )
        print(f"Stopped {stopped} workers")
    finally:
        manager.close()


def cmd_status(args):
    """Get worker status command"""
    manager = WorkerManager()
    try:
        if args.health:
            health = manager.check_worker_health()
            print(f"Worker Health Status ({health['checked_at']})")
            print(f"  Total: {health['total']}")
            print(f"  Alive: {health['alive']}")
            print(f"  Dead:  {health['dead']}")
            print(f"  Stale: {health['stale']}")
        else:
            workers = manager.get_worker_status()
            print(f"{'Worker ID':<40} {'Type':<10} {'Status':<10} {'Jobs':<10}")
            print("-" * 80)
            for w in workers:
                print(f"{w['worker_id']:<40} {w['worker_type']:<10} {w['status']:<10} {w['jobs_completed']:<10}")
    finally:
        manager.close()


def cmd_restart_dead(args):
    """Restart dead workers command"""
    manager = WorkerManager()
    try:
        restarted = manager.restart_dead_workers()
        print(f"Restarted {restarted} dead workers")
    finally:
        manager.close()


def main():
    parser = argparse.ArgumentParser(
        description="SlabHub Worker Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Start command
    start_parser = subparsers.add_parser("start", help="Start workers")
    start_parser.add_argument("--count", "-n", type=int, default=1, help="Number of workers")
    start_parser.add_argument("--type", "-t", default="default", help="Worker type")
    start_parser.add_argument("--queues", "-q", help="Comma-separated queue names")
    start_parser.add_argument("--monitor", "-m", action="store_true", help="Monitor workers")
    start_parser.set_defaults(func=cmd_start)

    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop all workers")
    stop_parser.add_argument("--force", "-f", action="store_true", help="Force stop")
    stop_parser.add_argument("--timeout", "-t", type=int, default=30, help="Graceful timeout")
    stop_parser.set_defaults(func=cmd_stop)

    # Status command
    status_parser = subparsers.add_parser("status", help="Get worker status")
    status_parser.add_argument("--health", action="store_true", help="Show health summary")
    status_parser.set_defaults(func=cmd_status)

    # Restart dead command
    restart_parser = subparsers.add_parser("restart-dead", help="Restart dead workers")
    restart_parser.set_defaults(func=cmd_restart_dead)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main() or 0)
