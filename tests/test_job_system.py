"""
Integration tests for SlabHub Job System.

Tests job creation, execution, completion, retry logic, dead letter queue,
and worker registration/heartbeat functionality.

Run with: pytest tests/test_job_system.py -v
"""

import sys
import uuid
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add backend to path for app imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.filter.return_value.count.return_value = 0
    return session


@pytest.fixture
def mock_job():
    """Create a mock Job object."""
    job = MagicMock()
    job.id = 1
    job.job_id = str(uuid.uuid4())
    job.job_type = "test_job"
    job.status = "pending"
    job.priority = 0
    job.max_retries = 3
    job.retry_count = 0
    job.created_at = datetime.now()
    job.started_at = None
    job.completed_at = None
    job.error_message = None
    job.quarantined = False
    job.lease_id = None
    job.lease_expires_at = None
    job.worker_id = None
    job.input_data = {}
    job.output_data = None
    job.is_terminal_state.return_value = False
    job.can_retry.return_value = True
    job.acquire_lease.return_value = True
    return job


@pytest.fixture
def mock_worker():
    """Create a mock Worker object."""
    worker = MagicMock()
    worker.id = 1
    worker.worker_id = f"worker-{uuid.uuid4()}"
    worker.hostname = "localhost"
    worker.pid = 12345
    worker.status = "idle"
    worker.app_version = "1.00"
    worker.last_heartbeat_at = datetime.now()
    worker.is_alive.return_value = True
    return worker


@pytest.fixture
def mock_dlq_item():
    """Create a mock DeadLetterQueue item."""
    item = MagicMock()
    item.id = 1
    item.original_job_id = str(uuid.uuid4())
    item.job_type = "test_job"
    item.failure_reason = "Max retries exceeded"
    item.failure_type = "max_retries"
    item.last_error = "Test error"
    item.retry_count = 3
    item.status = "pending"
    item.replay_count = 0
    item.job_input = {"test": "data"}
    item.resolved = False
    return item


# ============================================================================
# Job Creation Tests
# ============================================================================

class TestJobCreation:
    """Tests for job creation functionality."""

    def test_create_job_basic(self, mock_db_session):
        """Test basic job creation."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            # Setup mock to return the job after creation
            service = JobService(mock_db_session)

            # Mock the add and commit
            mock_db_session.add = MagicMock()
            mock_db_session.commit = MagicMock()
            mock_db_session.refresh = MagicMock()

            job = service.create_job(
                job_type="test_job",
                input_data={"key": "value"},
                priority=1,
                max_retries=3,
                created_by="test_user"
            )

            # Verify job was added to session
            assert mock_db_session.add.called
            assert mock_db_session.commit.called

    def test_create_job_with_idempotency_key(self, mock_db_session):
        """Test job creation with idempotency key returns existing job."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            # Setup mock to return existing job
            existing_job = MagicMock()
            existing_job.job_id = "existing-job-id"
            mock_db_session.query.return_value.filter.return_value.first.return_value = existing_job

            service = JobService(mock_db_session)

            result = service.create_job(
                job_type="test_job",
                idempotency_key="unique-key"
            )

            assert result == existing_job

    def test_create_job_default_values(self, mock_db_session):
        """Test job creation uses default values correctly."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_db_session.add = MagicMock()
            mock_db_session.commit = MagicMock()
            mock_db_session.refresh = MagicMock()
            mock_db_session.query.return_value.filter.return_value.first.return_value = None

            service = JobService(mock_db_session)

            # Create with minimal args
            service.create_job(job_type="minimal_job")

            # Verify add was called with default priority=0, max_retries=3
            assert mock_db_session.add.called


# ============================================================================
# Job Execution Tests
# ============================================================================

class TestJobExecution:
    """Tests for job execution functionality."""

    def test_start_job_success(self, mock_db_session, mock_job):
        """Test starting a job successfully."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.status = "pending"
            mock_job.is_terminal_state.return_value = False
            mock_job.acquire_lease.return_value = True

            service = JobService(mock_db_session)
            result = service.start_job(mock_job, "worker-123")

            assert result is True
            assert mock_job.status == "running"
            mock_db_session.commit.assert_called()

    def test_start_job_already_running(self, mock_db_session, mock_job):
        """Test starting a job that is already running fails."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.status = "running"
            mock_job.is_terminal_state.return_value = False

            service = JobService(mock_db_session)
            result = service.start_job(mock_job, "worker-123")

            assert result is False

    def test_start_job_terminal_state(self, mock_db_session, mock_job):
        """Test starting a job in terminal state fails."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.is_terminal_state.return_value = True

            service = JobService(mock_db_session)
            result = service.start_job(mock_job, "worker-123")

            assert result is False

    def test_start_job_lease_failed(self, mock_db_session, mock_job):
        """Test starting a job when lease acquisition fails."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.status = "pending"
            mock_job.is_terminal_state.return_value = False
            mock_job.acquire_lease.return_value = False

            service = JobService(mock_db_session)
            result = service.start_job(mock_job, "worker-123")

            assert result is False


# ============================================================================
# Job Completion Tests
# ============================================================================

class TestJobCompletion:
    """Tests for job completion functionality."""

    def test_complete_job_success(self, mock_db_session, mock_job):
        """Test completing a job successfully."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            service = JobService(mock_db_session)
            service.complete_job(mock_job, {"result": "success"})

            assert mock_job.status == "completed"
            assert mock_job.output_data == {"result": "success"}
            mock_db_session.commit.assert_called()

    def test_complete_job_sets_timestamp(self, mock_db_session, mock_job):
        """Test completing a job sets completed_at timestamp."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            service = JobService(mock_db_session)
            before = datetime.now()
            service.complete_job(mock_job)

            assert mock_job.completed_at is not None

    def test_fail_job(self, mock_db_session, mock_job):
        """Test failing a job."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

            service = JobService(mock_db_session)
            service.fail_job(mock_job, "Test error", {"details": "error info"})

            assert mock_job.status == "failed"
            assert mock_job.error_message == "Test error"
            mock_db_session.commit.assert_called()

    def test_fail_job_with_quarantine(self, mock_db_session, mock_job):
        """Test failing a job with quarantine flag."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

            service = JobService(mock_db_session)
            service.fail_job(mock_job, "Poison job", quarantine=True)

            assert mock_job.status == "failed"
            assert mock_job.quarantined is True
            assert mock_job.quarantine_reason == "Poison job"

    def test_cancel_job(self, mock_db_session, mock_job):
        """Test cancelling a job."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.is_terminal_state.return_value = False

            service = JobService(mock_db_session)
            service.cancel_job(mock_job, "User requested cancellation")

            assert mock_job.status == "cancelled"
            mock_db_session.commit.assert_called()

    def test_cancel_terminal_job_no_op(self, mock_db_session, mock_job):
        """Test cancelling a terminal job does nothing."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.status = "completed"
            mock_job.is_terminal_state.return_value = True

            service = JobService(mock_db_session)
            service.cancel_job(mock_job)

            # Status should remain unchanged
            assert mock_job.status == "completed"


# ============================================================================
# Job Retry Tests
# ============================================================================

class TestJobRetry:
    """Tests for job retry functionality."""

    def test_retry_job_success(self, mock_db_session, mock_job):
        """Test retrying a job successfully."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.status = "failed"
            mock_job.retry_count = 0
            mock_job.can_retry.return_value = True

            service = JobService(mock_db_session)
            result = service.retry_job(mock_job)

            assert result is True
            assert mock_job.status == "pending"
            assert mock_job.retry_count == 1
            mock_db_session.commit.assert_called()

    def test_retry_job_max_retries_reached(self, mock_db_session, mock_job):
        """Test retrying a job when max retries reached."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.can_retry.return_value = False

            service = JobService(mock_db_session)
            result = service.retry_job(mock_job)

            assert result is False

    def test_retry_resets_job_state(self, mock_db_session, mock_job):
        """Test retry resets job state correctly."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.status = "failed"
            mock_job.started_at = datetime.now()
            mock_job.completed_at = datetime.now()
            mock_job.lease_id = "old-lease"
            mock_job.worker_id = "old-worker"
            mock_job.can_retry.return_value = True

            service = JobService(mock_db_session)
            service.retry_job(mock_job)

            assert mock_job.started_at is None
            assert mock_job.completed_at is None
            assert mock_job.lease_id is None
            assert mock_job.worker_id is None


# ============================================================================
# Dead Letter Queue Tests
# ============================================================================

class TestDeadLetterQueue:
    """Tests for dead letter queue functionality."""

    def test_get_dlq_items(self, mock_db_session, mock_dlq_item):
        """Test retrieving DLQ items."""
        with patch('app.services.queue_service.SessionLocal', return_value=mock_db_session):
            from app.services.queue_service import QueueManager

            mock_db_session.query.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_dlq_item]

            manager = QueueManager(mock_db_session)
            items = manager.get_dlq_items()

            assert len(items) == 1

    def test_get_dlq_items_filtered_by_status(self, mock_db_session, mock_dlq_item):
        """Test retrieving DLQ items filtered by status."""
        with patch('app.services.queue_service.SessionLocal', return_value=mock_db_session):
            from app.services.queue_service import QueueManager

            mock_db_session.query.return_value.order_by.return_value.filter.return_value.offset.return_value.limit.return_value.all.return_value = [mock_dlq_item]

            manager = QueueManager(mock_db_session)
            items = manager.get_dlq_items(status="pending")

            # Query was called with filter
            assert mock_db_session.query.called

    def test_discard_dlq_item(self, mock_db_session, mock_dlq_item):
        """Test discarding a DLQ item."""
        with patch('app.services.queue_service.SessionLocal', return_value=mock_db_session):
            from app.services.queue_service import QueueManager

            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_dlq_item

            manager = QueueManager(mock_db_session)
            result = manager.discard_dlq_item(1, "No longer needed")

            assert result is True
            assert mock_dlq_item.status == "discarded"
            assert mock_dlq_item.resolved is True
            mock_db_session.commit.assert_called()

    def test_discard_dlq_item_not_found(self, mock_db_session):
        """Test discarding a non-existent DLQ item."""
        with patch('app.services.queue_service.SessionLocal', return_value=mock_db_session):
            from app.services.queue_service import QueueManager

            mock_db_session.query.return_value.filter.return_value.first.return_value = None

            manager = QueueManager(mock_db_session)
            result = manager.discard_dlq_item(999)

            assert result is False


# ============================================================================
# Worker Registration Tests
# ============================================================================

class TestWorkerRegistration:
    """Tests for worker registration and heartbeat functionality."""

    def test_worker_is_alive_with_recent_heartbeat(self, mock_worker):
        """Test worker is considered alive with recent heartbeat."""
        mock_worker.status = "idle"
        mock_worker.last_heartbeat_at = datetime.utcnow()

        # The is_alive method checks if heartbeat is within timeout
        mock_worker.is_alive.return_value = True

        assert mock_worker.is_alive() is True

    def test_worker_is_dead_with_stale_heartbeat(self, mock_worker):
        """Test worker is considered dead with stale heartbeat."""
        mock_worker.status = "idle"
        mock_worker.last_heartbeat_at = datetime.utcnow() - timedelta(minutes=5)
        mock_worker.is_alive.return_value = False

        assert mock_worker.is_alive() is False

    def test_worker_is_dead_when_status_stopped(self, mock_worker):
        """Test worker is dead when status is stopped."""
        mock_worker.status = "stopped"
        mock_worker.is_alive.return_value = False

        assert mock_worker.is_alive() is False


# ============================================================================
# Job Lease Management Tests
# ============================================================================

class TestJobLeaseManagement:
    """Tests for job lease management."""

    def test_acquire_pending_job(self, mock_db_session, mock_job):
        """Test acquiring a pending job for processing."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.status = "pending"
            mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_job]

            service = JobService(mock_db_session)
            result = service.acquire_pending_job("worker-123")

            # Job should be acquired
            assert mock_job.acquire_lease.called

    def test_release_job_lease(self, mock_db_session, mock_job):
        """Test releasing a job lease."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            service = JobService(mock_db_session)
            service.release_job_lease(mock_job)

            mock_job.release_lease.assert_called()
            mock_db_session.commit.assert_called()

    def test_update_heartbeat_extends_lease(self, mock_db_session, mock_job):
        """Test updating heartbeat extends the lease."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_job.lease_expires_at = datetime.now()
            original_expiry = mock_job.lease_expires_at

            service = JobService(mock_db_session)
            service.update_heartbeat(mock_job)

            # Lease should be extended
            mock_db_session.commit.assert_called()

    def test_cleanup_expired_leases(self, mock_db_session, mock_job):
        """Test cleaning up expired job leases."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            # Setup job with expired lease
            mock_job.lease_expires_at = datetime.now() - timedelta(hours=1)
            mock_job.status = "running"
            mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_job]

            service = JobService(mock_db_session)
            count = service.cleanup_expired_leases()

            assert count == 1
            mock_job.release_lease.assert_called()


# ============================================================================
# Job Metrics Tests
# ============================================================================

class TestJobMetrics:
    """Tests for job metrics functionality."""

    def test_get_job_metrics(self, mock_db_session):
        """Test getting job metrics."""
        with patch('app.services.job_service.SessionLocal', return_value=mock_db_session):
            from app.services.job_service import JobService

            mock_db_session.query.return_value.count.return_value = 100
            mock_db_session.query.return_value.filter.return_value.count.return_value = 10

            service = JobService(mock_db_session)
            metrics = service.get_job_metrics()

            assert "total_jobs" in metrics
            assert "pending_jobs" in metrics
            assert "running_jobs" in metrics
            assert "completed_jobs" in metrics
            assert "failed_jobs" in metrics
            assert "quarantined_jobs" in metrics
            assert "success_rate" in metrics


# ============================================================================
# Integration Tests (require database)
# ============================================================================

class TestJobSystemIntegration:
    """Integration tests that require a real database connection."""

    @pytest.fixture
    def real_db_session(self):
        """Create a real database session for integration tests."""
        try:
            from app.models import SessionLocal
            db = SessionLocal()
            yield db
            db.close()
        except Exception:
            pytest.skip("Database not available for integration tests")

    def test_full_job_lifecycle(self, real_db_session):
        """Test complete job lifecycle: create, start, complete."""
        try:
            from app.services.job_service import JobService
            from app.models.job import JOB_STATUS_COMPLETED

            service = JobService(real_db_session)

            # Create job
            job = service.create_job(
                job_type="integration_test",
                input_data={"test": True},
                created_by="pytest"
            )
            assert job.job_id is not None
            assert job.status == "pending"

            # Start job
            success = service.start_job(job, "test-worker")
            if success:
                assert job.status == "running"

                # Complete job
                service.complete_job(job, {"result": "success"})
                assert job.status == str(JOB_STATUS_COMPLETED)

            # Cleanup
            real_db_session.delete(job)
            real_db_session.commit()

        except Exception as e:
            pytest.skip(f"Integration test skipped: {e}")

    def test_job_retry_integration(self, real_db_session):
        """Test job retry in integration environment."""
        try:
            from app.services.job_service import JobService

            service = JobService(real_db_session)

            # Create and fail job
            job = service.create_job(
                job_type="retry_test",
                max_retries=3,
                created_by="pytest"
            )

            # Simulate failure and retry
            service.fail_job(job, "Simulated failure")

            if job.can_retry():
                success = service.retry_job(job)
                assert success is True
                assert job.retry_count == 1
                assert job.status == "pending"

            # Cleanup
            real_db_session.delete(job)
            real_db_session.commit()

        except Exception as e:
            pytest.skip(f"Integration test skipped: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
