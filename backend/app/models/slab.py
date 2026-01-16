"""
Slab model for stone inventory management
Tracks individual stone slabs with detailed attributes, images, and metadata
"""
from datetime import datetime
from sqlalchemy import (
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Index,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.models.base import Base


class Slab(Base):
    """
    Stone slab inventory model

    Represents a single stone slab with all relevant attributes for
    inventory management, including physical properties, location,
    pricing, images, and import metadata.
    """
    __tablename__ = "slabs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Public identifier for QR codes and external references
    public_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique public identifier for QR codes"
    )

    # Basic information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Slab name or identifier"
    )

    stone_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Type of stone (granite, marble, quartzite, etc.)"
    )

    supplier: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        index=True,
        comment="Supplier or vendor name"
    )

    finish: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Surface finish (polished, honed, leathered, etc.)"
    )

    thickness: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Thickness in inches"
    )

    color: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Primary color or color description"
    )

    # Dimensions and area
    length: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Length in inches"
    )

    width: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Width in inches"
    )

    square_feet: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Total square footage"
    )

    # Location and status
    location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Physical storage location"
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        server_default="available",
        comment="Status (available, reserved, sold, damaged, etc.)"
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="1",
        comment="Number of identical slabs"
    )

    # Additional metadata
    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated tags for categorization"
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes and comments"
    )

    # Images
    primary_image: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to primary/featured image"
    )

    additional_images: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Array of additional image paths"
    )

    # Flexible storage for unmapped import data
    extra_json: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Extra fields from imports that don't map to defined columns"
    )

    # Pricing
    cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Cost price"
    )

    price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Selling price"
    )

    # Timestamps
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

    # Import tracking
    import_source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Source of import (excel, csv, api, etc.)"
    )

    import_batch_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Batch ID from import process"
    )

    # Image duplicate detection
    perceptual_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Perceptual hash for duplicate image detection"
    )

    # QR code
    qr_code_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        unique=True,
        comment="Path to generated QR code image"
    )

    # Additional indexes for common queries
    __table_args__ = (
        Index("idx_slab_status_location", "status", "location"),
        Index("idx_slab_supplier_stone_type", "supplier", "stone_type"),
        Index("idx_slab_import_batch", "import_batch_id"),
    )

    def __repr__(self) -> str:
        return f"<Slab(id={self.id}, public_id='{self.public_id}', name='{self.name}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "public_id": self.public_id,
            "name": self.name,
            "stone_type": self.stone_type,
            "supplier": self.supplier,
            "finish": self.finish,
            "thickness": self.thickness,
            "color": self.color,
            "length": self.length,
            "width": self.width,
            "square_feet": self.square_feet,
            "location": self.location,
            "status": self.status,
            "quantity": self.quantity,
            "tags": self.tags,
            "notes": self.notes,
            "primary_image": self.primary_image,
            "additional_images": self.additional_images,
            "extra_json": self.extra_json,
            "cost": self.cost,
            "price": self.price,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "import_source": self.import_source,
            "import_batch_id": self.import_batch_id,
            "perceptual_hash": self.perceptual_hash,
            "qr_code_path": self.qr_code_path,
        }
