"""
Pytest configuration and shared fixtures for SlabHub tests.

This file provides common fixtures used across all test modules.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# Global Test Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (may require database)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """
    Create a mock database session.

    This fixture provides a MagicMock object that simulates
    a SQLAlchemy session for unit testing.
    """
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.refresh = MagicMock()
    session.delete = MagicMock()
    session.execute = MagicMock(return_value=True)

    # Default query behavior
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.filter.return_value.count.return_value = 0
    session.query.return_value.first.return_value = None
    session.query.return_value.all.return_value = []
    session.query.return_value.count.return_value = 0

    return session


@pytest.fixture
def real_db_session():
    """
    Create a real database session for integration tests.

    This fixture attempts to create a real database connection.
    If the database is not available, the test is skipped.
    """
    try:
        from backend.app.models import SessionLocal
        db = SessionLocal()
        yield db
        db.rollback()  # Rollback any uncommitted changes
        db.close()
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


# ============================================================================
# App and Client Fixtures
# ============================================================================

@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = MagicMock()
    settings.debug = True
    settings.database_url = "sqlite:///test.db"
    settings.slabhub_root = str(project_root)
    settings.public_base_url = "http://localhost:8000"
    settings.enable_watch_folder = False
    settings.openai_api_key = "test-key"
    settings.openai_model = "gpt-4o"
    settings.log_level = "INFO"
    settings.host = "0.0.0.0"
    settings.port = 8000
    return settings


@pytest.fixture
def test_client_factory():
    """
    Factory fixture to create test clients with custom configuration.

    Usage:
        def test_something(test_client_factory):
            client = test_client_factory(mock_db=my_mock_db)
            response = client.get("/health")
    """
    def _create_client(mock_db=None):
        try:
            from fastapi.testclient import TestClient

            with patch('backend.app.main.init_db'):
                with patch('backend.app.main.WatchFolderService'):
                    with patch('backend.app.main.SessionLocal') as mock_session_local:
                        if mock_db:
                            mock_session_local.return_value = mock_db
                        else:
                            mock_session_local.return_value = MagicMock()

                        from backend.app.main import app
                        return TestClient(app)
        except Exception as e:
            pytest.skip(f"Could not create test client: {e}")

    return _create_client


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def mock_job():
    """Create a mock Job object."""
    import uuid
    from datetime import datetime

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
    job.release_lease = MagicMock()
    job.to_dict.return_value = {
        "id": job.id,
        "job_id": job.job_id,
        "job_type": job.job_type,
        "status": job.status,
    }
    return job


@pytest.fixture
def mock_worker():
    """Create a mock Worker object."""
    import uuid
    from datetime import datetime

    worker = MagicMock()
    worker.id = 1
    worker.worker_id = f"worker-{uuid.uuid4()}"
    worker.hostname = "localhost"
    worker.pid = 12345
    worker.status = "idle"
    worker.app_version = "1.00"
    worker.last_heartbeat_at = datetime.now()
    worker.is_alive.return_value = True
    worker.to_dict.return_value = {
        "worker_id": worker.worker_id,
        "status": worker.status,
        "is_alive": True,
    }
    return worker


@pytest.fixture
def mock_circuit_breaker():
    """Create a mock GPT circuit breaker object."""
    from datetime import datetime

    circuit = MagicMock()
    circuit.circuit_name = "openai_default"
    circuit.state = "closed"
    circuit.failure_count = 0
    circuit.success_count = 0
    circuit.failure_threshold = 5
    circuit.success_threshold = 3
    circuit.open_duration_seconds = 60
    circuit.is_disabled = False
    circuit.disabled_reason = None
    circuit.opened_at = None
    circuit.last_failure_at = None
    return circuit


@pytest.fixture
def mock_ledger_entry():
    """Create a mock agent ledger entry."""
    import uuid
    from datetime import datetime

    entry = MagicMock()
    entry.id = 1
    entry.entry_id = str(uuid.uuid4())
    entry.agent_name = "test-agent"
    entry.agent_session_id = "test-session"
    entry.action_type = "fix"
    entry.description = "Test action"
    entry.version_before = "1.00"
    entry.version_after = "1.01"
    entry.is_compliant = True
    entry.violations = None
    entry.reviewed = False
    entry.created_at = datetime.now()
    entry.to_dict.return_value = {
        "entry_id": entry.entry_id,
        "action_type": entry.action_type,
        "is_compliant": entry.is_compliant,
    }
    return entry


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def temp_file(tmp_path):
    """Create a temporary file for testing."""
    def _create_file(name="test.txt", content="test content"):
        file_path = tmp_path / name
        file_path.write_text(content)
        return file_path
    return _create_file


@pytest.fixture
def temp_image(tmp_path):
    """Create a temporary image file for testing."""
    def _create_image(name="test.jpg"):
        file_path = tmp_path / name
        # Write minimal JPEG header
        file_path.write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)
        return file_path
    return _create_image


# ============================================================================
# Skip Conditions
# ============================================================================

@pytest.fixture
def skip_if_no_db():
    """Skip test if database is not available."""
    try:
        from backend.app.models import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception:
        pytest.skip("Database not available")


@pytest.fixture
def skip_if_no_openai():
    """Skip test if OpenAI API is not configured."""
    try:
        from backend.app.config import settings
        if not settings.openai_api_key or settings.openai_api_key == "test-key":
            pytest.skip("OpenAI API key not configured")
    except Exception:
        pytest.skip("Settings not available")
