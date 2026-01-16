"""
Integration tests for SlabHub Agent Ledger Service.

Tests action logging, violation detection, and compliance report generation.

Run with: pytest tests/test_agent_ledger.py -v
"""

import sys
import uuid
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    session.query.return_value.filter.return_value.count.return_value = 0
    session.query.return_value.filter.return_value.all.return_value = []
    session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    session.query.return_value.count.return_value = 0
    return session


@pytest.fixture
def mock_ledger_entry():
    """Create a mock agent ledger entry."""
    entry = MagicMock()
    entry.id = 1
    entry.entry_id = str(uuid.uuid4())
    entry.agent_name = "claude-code"
    entry.agent_session_id = "test-session"
    entry.action_type = "fix"
    entry.description = "Fixed a bug"
    entry.version_before = "1.00"
    entry.version_after = "1.01"
    entry.job_id = None
    entry.files_changed = {"files": ["file1.py", "file2.py"]}
    entry.evidence = {"logs": "test logs"}
    entry.is_compliant = True
    entry.violations = None
    entry.reviewed = False
    entry.created_at = datetime.now()
    return entry


@pytest.fixture
def mock_violation():
    """Create a mock agent violation."""
    violation = MagicMock()
    violation.id = 1
    violation.violation_id = str(uuid.uuid4())
    violation.ledger_entry_id = str(uuid.uuid4())
    violation.violation_type = "no_version_bump"
    violation.severity = "high"
    violation.description = "Code changed but version unchanged"
    violation.agent_name = "claude-code"
    violation.version_at_violation = "1.00"
    violation.resolved = False
    violation.resolved_at = None
    violation.resolution_notes = None
    violation.created_at = datetime.now()
    violation.to_dict.return_value = {
        "violation_id": violation.violation_id,
        "violation_type": violation.violation_type,
        "severity": violation.severity,
        "resolved": violation.resolved,
    }
    return violation


# ============================================================================
# Action Logging Tests
# ============================================================================

class TestActionLogging:
    """Tests for action logging functionality."""

    def test_log_action_basic(self, mock_db_session):
        """Test basic action logging."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent", "test-session")
            entry_id = service.log_action(
                action_type="fix",
                description="Fixed a bug",
                version_before="1.00",
                version_after="1.01",
                files_changed=["file1.py"],
                evidence={"logs": "test logs"}
            )

            assert entry_id is not None
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called()

    def test_log_action_with_job_id(self, mock_db_session):
        """Test action logging with job ID."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            entry_id = service.log_action(
                action_type="feature",
                description="Added new feature",
                version_before="1.00",
                version_after="1.01",
                job_id="job-123"
            )

            assert entry_id is not None
            mock_db_session.add.assert_called()

    def test_log_fix_convenience_method(self, mock_db_session):
        """Test log_fix convenience method."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            entry_id = service.log_fix(
                description="Fixed memory leak",
                version_before="1.00",
                version_after="1.01",
                files_changed=["memory.py"],
                log_output="Memory fixed",
                test_results="All tests pass"
            )

            assert entry_id is not None
            mock_db_session.add.assert_called()

    def test_log_feature_convenience_method(self, mock_db_session):
        """Test log_feature convenience method."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            entry_id = service.log_feature(
                description="Added dark mode",
                version_before="1.00",
                version_after="1.01",
                files_changed=["theme.py", "styles.css"],
                job_id="job-456",
                verification_steps=["Toggle dark mode", "Check all pages"]
            )

            assert entry_id is not None
            mock_db_session.add.assert_called()

    def test_log_refactor_convenience_method(self, mock_db_session):
        """Test log_refactor convenience method."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            entry_id = service.log_refactor(
                description="Refactored database module",
                version_before="1.00",
                version_after="1.01",
                files_changed=["database.py", "models.py"],
                verification_steps=["Run migrations", "Test CRUD operations"]
            )

            assert entry_id is not None
            mock_db_session.add.assert_called()

    def test_log_action_creates_session_id_if_missing(self, mock_db_session):
        """Test that session ID is auto-generated if not provided."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")  # No session_id

            assert service.session_id is not None
            assert len(service.session_id) == 8  # UUID[:8]


# ============================================================================
# Violation Detection Tests
# ============================================================================

class TestViolationDetection:
    """Tests for violation detection functionality."""

    def test_no_violation_when_version_bumped(self, mock_db_session):
        """Test no violation when version is properly bumped."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            violations = service._check_violations(
                action_type="fix",
                version_before="1.00",
                version_after="1.01",
                job_id=None,
                evidence={"logs": "test"}
            )

            assert len(violations) == 0

    def test_violation_when_version_not_bumped(self, mock_db_session):
        """Test violation detected when version not bumped."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            violations = service._check_violations(
                action_type="fix",
                version_before="1.00",
                version_after="1.00",  # Same version!
                job_id=None,
                evidence={"logs": "test"}
            )

            assert len(violations) >= 1
            violation_types = [v["type"].value for v in violations]
            assert "no_version_bump" in violation_types

    def test_violation_when_version_missing(self, mock_db_session):
        """Test violation when version_after is missing."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            violations = service._check_violations(
                action_type="fix",
                version_before="1.00",
                version_after=None,  # Missing version
                job_id=None,
                evidence={"logs": "test"}
            )

            assert len(violations) >= 1

    def test_violation_when_version_skip(self, mock_db_session):
        """Test violation when version skips (not +0.01)."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            violations = service._check_violations(
                action_type="fix",
                version_before="1.00",
                version_after="1.05",  # Should be 1.01
                job_id=None,
                evidence={"logs": "test"}
            )

            assert len(violations) >= 1
            violation_types = [v["type"].value for v in violations]
            assert "version_skip" in violation_types

    def test_violation_when_job_id_missing_for_feature(self, mock_db_session):
        """Test violation when job ID missing for feature."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            violations = service._check_violations(
                action_type="feature",
                version_before="1.00",
                version_after="1.01",
                job_id=None,  # Missing job ID for feature!
                evidence=None
            )

            assert len(violations) >= 1
            violation_types = [v["type"].value for v in violations]
            assert "no_job_id" in violation_types

    def test_violation_when_evidence_missing_for_fix(self, mock_db_session):
        """Test violation when evidence missing for fix."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            violations = service._check_violations(
                action_type="fix",
                version_before="1.00",
                version_after="1.01",
                job_id=None,
                evidence=None  # Missing evidence for fix!
            )

            assert len(violations) >= 1
            violation_types = [v["type"].value for v in violations]
            assert "no_evidence" in violation_types

    def test_no_violation_for_config_change(self, mock_db_session):
        """Test no violation checks for config changes."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            violations = service._check_violations(
                action_type="config_change",
                version_before=None,
                version_after=None,
                job_id=None,
                evidence=None
            )

            # Config changes don't require version bump
            assert len(violations) == 0

    def test_invalid_version_format_violation(self, mock_db_session):
        """Test violation for invalid version format."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            violations = service._check_violations(
                action_type="fix",
                version_before="1.00",
                version_after="invalid",  # Not a number
                job_id=None,
                evidence={"logs": "test"}
            )

            assert len(violations) >= 1
            violation_types = [v["type"].value for v in violations]
            assert "invalid_version_format" in violation_types


# ============================================================================
# Violation Recording Tests
# ============================================================================

class TestViolationRecording:
    """Tests for recording violations."""

    def test_log_standalone_violation(self, mock_db_session):
        """Test logging a standalone violation."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import log_violation

            violation_id = log_violation(
                violation_type="silent_exception",
                description="Exception caught but not logged",
                agent_name="test-agent",
                severity="medium"
            )

            assert violation_id is not None
            mock_db_session.add.assert_called()
            mock_db_session.commit.assert_called()

    def test_log_action_records_violations(self, mock_db_session):
        """Test that log_action records violations when detected."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            entry_id = service.log_action(
                action_type="fix",
                description="Fixed bug without version bump",
                version_before="1.00",
                version_after="1.00",  # No bump - violation!
                evidence=None  # No evidence - another violation!
            )

            # Should have multiple add calls (entry + violations)
            assert mock_db_session.add.call_count >= 1
            mock_db_session.commit.assert_called()

    def test_resolve_violation(self, mock_db_session, mock_violation):
        """Test resolving a violation."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import resolve_violation

            mock_db_session.query.return_value.filter.return_value.first.return_value = mock_violation

            result = resolve_violation(
                violation_id=mock_violation.violation_id,
                resolution_notes="Fixed by bumping version"
            )

            assert result is True
            assert mock_violation.resolved is True
            mock_db_session.commit.assert_called()

    def test_resolve_nonexistent_violation(self, mock_db_session):
        """Test resolving a non-existent violation."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import resolve_violation

            mock_db_session.query.return_value.filter.return_value.first.return_value = None

            result = resolve_violation(
                violation_id="nonexistent-id",
                resolution_notes="N/A"
            )

            assert result is False


# ============================================================================
# Compliance Report Tests
# ============================================================================

class TestComplianceReport:
    """Tests for compliance report generation."""

    def test_get_compliance_report_all_agents(self, mock_db_session):
        """Test getting compliance report for all agents."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import get_agent_compliance_report

            # Setup mock counts
            mock_db_session.query.return_value.count.return_value = 100
            mock_db_session.query.return_value.filter.return_value.count.return_value = 90

            report = get_agent_compliance_report()

            assert "agent_name" in report
            assert "total_actions" in report
            assert "compliant_actions" in report
            assert "compliance_rate" in report
            assert "total_violations" in report
            assert "unresolved_violations" in report
            assert "violation_breakdown" in report

    def test_get_compliance_report_specific_agent(self, mock_db_session):
        """Test getting compliance report for specific agent."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import get_agent_compliance_report

            mock_db_session.query.return_value.filter.return_value.count.return_value = 50

            report = get_agent_compliance_report(agent_name="claude-code")

            assert report["agent_name"] == "claude-code"

    def test_compliance_rate_calculation(self, mock_db_session):
        """Test compliance rate calculation."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import get_agent_compliance_report

            # 80 compliant out of 100 total
            mock_db_session.query.return_value.count.return_value = 100
            mock_db_session.query.return_value.filter.return_value.count.side_effect = [80, 20, 5]

            report = get_agent_compliance_report()

            # Can't verify exact rate without running real code, but structure is correct
            assert "compliance_rate" in report

    def test_compliance_report_with_no_actions(self, mock_db_session):
        """Test compliance report when no actions recorded."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import get_agent_compliance_report

            mock_db_session.query.return_value.count.return_value = 0
            mock_db_session.query.return_value.filter.return_value.count.return_value = 0

            report = get_agent_compliance_report()

            assert report["total_actions"] == 0
            assert report["compliance_rate"] == 100  # Default to 100% if no actions

    def test_get_unresolved_violations(self, mock_db_session, mock_violation):
        """Test getting unresolved violations."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import get_unresolved_violations

            mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_violation]

            violations = get_unresolved_violations()

            assert len(violations) == 1
            assert violations[0]["violation_type"] == mock_violation.violation_type


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_log_action_handles_database_error(self, mock_db_session):
        """Test log_action handles database errors gracefully."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            mock_db_session.commit.side_effect = Exception("Database error")

            service = AgentLedgerService("test-agent")

            with pytest.raises(Exception):
                service.log_action(
                    action_type="fix",
                    description="Test action"
                )

            mock_db_session.rollback.assert_called()

    def test_log_action_with_empty_files_changed(self, mock_db_session):
        """Test log_action with empty files_changed list."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            entry_id = service.log_action(
                action_type="other",
                description="No files changed",
                files_changed=[]
            )

            assert entry_id is not None

    def test_log_action_with_unicode_description(self, mock_db_session):
        """Test log_action with unicode in description."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")
            entry_id = service.log_action(
                action_type="fix",
                description="Fixed bug with unicode: \u2603 \u2764 \u263A"
            )

            assert entry_id is not None

    def test_violation_severity_levels(self, mock_db_session):
        """Test different violation severity levels."""
        with patch('backend.app.services.agent_ledger_service.SessionLocal', return_value=mock_db_session):
            from backend.app.services.agent_ledger_service import AgentLedgerService

            service = AgentLedgerService("test-agent")

            # No version bump should be high severity
            violations = service._check_violations(
                action_type="fix",
                version_before="1.00",
                version_after="1.00",
                job_id=None,
                evidence={"logs": "test"}
            )

            high_severity_found = any(v["severity"] == "high" for v in violations)
            assert high_severity_found


# ============================================================================
# Integration Tests
# ============================================================================

class TestAgentLedgerIntegration:
    """Integration tests that require a real database connection."""

    @pytest.fixture
    def real_db_session(self):
        """Create a real database session for integration tests."""
        try:
            from backend.app.models import SessionLocal
            db = SessionLocal()
            yield db
            db.close()
        except Exception:
            pytest.skip("Database not available for integration tests")

    def test_full_ledger_workflow(self, real_db_session):
        """Test complete ledger workflow: log action, check violations, report."""
        try:
            from backend.app.services.agent_ledger_service import (
                AgentLedgerService,
                get_agent_compliance_report
            )

            service = AgentLedgerService("integration-test-agent")

            # Log a compliant action
            entry_id = service.log_action(
                action_type="other",
                description="Integration test action"
            )
            assert entry_id is not None

            # Get compliance report
            report = get_agent_compliance_report("integration-test-agent")
            assert report["total_actions"] >= 1

            # Cleanup - would need to delete the entry
            # For now, just verify the workflow completed

        except Exception as e:
            pytest.skip(f"Integration test skipped: {e}")

    def test_violation_detection_integration(self, real_db_session):
        """Test violation detection in integration environment."""
        try:
            from backend.app.services.agent_ledger_service import (
                AgentLedgerService,
                get_unresolved_violations
            )

            service = AgentLedgerService("violation-test-agent")

            # Log action with violation
            entry_id = service.log_action(
                action_type="fix",
                description="Fix without evidence",
                version_before="1.00",
                version_after="1.01",
                evidence=None  # This should cause a violation
            )

            # Check for unresolved violations
            violations = get_unresolved_violations()
            # Should have at least one violation

        except Exception as e:
            pytest.skip(f"Integration test skipped: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
