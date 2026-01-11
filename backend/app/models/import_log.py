"""
Import log model for tracking data import operations
Records batch imports, status, errors, and statistics
"""
from datetime import datetime
from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    Index,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.models.base import Base


class ImportLog(Base):
    """
    Import operation log model

    Tracks all data import operations including batch imports from Excel,
    CSV, or other sources. Records statistics, errors, and warnings for
    audit and troubleshooting purposes.
    """
    __tablename__ = "import_logs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Batch identification
    batch_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique batch identifier (typically UUID)"
    )

    # Import metadata
    import_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of import (excel, csv, api, manual, etc.)"
    )

    source_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to source file or data location"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        server_default="running",
        comment="Status (running, completed, failed, partial)"
    )

    # Statistics
    items_processed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Total number of items processed"
    )

    items_success: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of items successfully imported"
    )

    items_failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of items that failed to import"
    )

    items_skipped: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Number of items skipped (duplicates, etc.)"
    )

    # Error and warning tracking
    errors: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Array of error messages with details"
    )

    warnings: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Array of warning messages"
    )

    # Summary
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable summary of import operation"
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Import start timestamp"
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Import completion timestamp"
    )

    # Standard timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Record creation timestamp"
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Record last update timestamp"
    )

    # Additional indexes for common queries
    __table_args__ = (
        Index("idx_import_type_status", "import_type", "status"),
        Index("idx_import_started_at", "started_at"),
    )

    def __repr__(self) -> str:
        return f"<ImportLog(id={self.id}, batch_id='{self.batch_id}', status='{self.status}', success={self.items_success})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "batch_id": self.batch_id,
            "import_type": self.import_type,
            "source_path": self.source_path,
            "status": self.status,
            "items_processed": self.items_processed,
            "items_success": self.items_success,
            "items_failed": self.items_failed,
            "items_skipped": self.items_skipped,
            "errors": self.errors,
            "warnings": self.warnings,
            "summary": self.summary,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def get_duration_seconds(self) -> float | None:
        """Calculate import duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def get_success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.items_processed == 0:
            return 0.0
        return (self.items_success / self.items_processed) * 100
