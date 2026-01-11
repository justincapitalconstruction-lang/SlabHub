"""
General inventory and shipment models
Manages non-slab inventory items and incoming shipments
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


class InventoryItem(Base):
    """
    General inventory item model

    For tracking supplies, tools, and other non-slab inventory items
    such as adhesives, sealers, tools, etc.
    """
    __tablename__ = "inventory_items"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Item identification
    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Stock keeping unit - unique identifier"
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Item name"
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed item description"
    )

    # Categorization
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Item category (adhesive, sealer, tool, etc.)"
    )

    # Unit of measure
    unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Unit of measure (each, box, gallon, etc.)"
    )

    # Quantity tracking
    qty_on_hand: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Current quantity in stock"
    )

    qty_reserved: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="Quantity reserved for orders"
    )

    reorder_point: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Minimum quantity before reordering"
    )

    # Location
    location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Physical storage location"
    )

    # Pricing
    unit_cost: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Cost per unit"
    )

    unit_price: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Selling price per unit"
    )

    # Additional metadata
    tags: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated tags"
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes"
    )

    # Images
    images: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Array of image paths"
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

    # Additional indexes
    __table_args__ = (
        Index("idx_inventory_category_location", "category", "location"),
    )

    def __repr__(self) -> str:
        return f"<InventoryItem(id={self.id}, sku='{self.sku}', name='{self.name}', qty={self.qty_on_hand})>"

    def to_dict(self) -> dict:
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "unit": self.unit,
            "qty_on_hand": self.qty_on_hand,
            "qty_reserved": self.qty_reserved,
            "qty_available": self.qty_on_hand - self.qty_reserved,
            "reorder_point": self.reorder_point,
            "location": self.location,
            "unit_cost": self.unit_cost,
            "unit_price": self.unit_price,
            "tags": self.tags,
            "notes": self.notes,
            "images": self.images,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Shipment(Base):
    """
    Shipment tracking model

    Tracks incoming shipments from suppliers including purchase orders,
    expected delivery dates, and received items.
    """
    __tablename__ = "shipments"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Shipment identification
    tracking_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Carrier tracking number"
    )

    supplier: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        comment="Supplier or vendor name"
    )

    po_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Purchase order number"
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        server_default="pending",
        comment="Status (pending, in_transit, received, cancelled, etc.)"
    )

    # Items in shipment (stored as JSON array)
    items: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Array of items in shipment with SKU, quantity, etc."
    )

    # Additional information
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Shipment notes and comments"
    )

    # Important dates
    ordered_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date order was placed"
    )

    expected_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Expected delivery date"
    )

    received_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Actual received date"
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

    # Additional indexes
    __table_args__ = (
        Index("idx_shipment_supplier_status", "supplier", "status"),
        Index("idx_shipment_expected_date", "expected_date"),
    )

    def __repr__(self) -> str:
        return f"<Shipment(id={self.id}, supplier='{self.supplier}', status='{self.status}')>"

    def to_dict(self) -> dict:
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "tracking_number": self.tracking_number,
            "supplier": self.supplier,
            "po_number": self.po_number,
            "status": self.status,
            "items": self.items,
            "notes": self.notes,
            "ordered_date": self.ordered_date.isoformat() if self.ordered_date else None,
            "expected_date": self.expected_date.isoformat() if self.expected_date else None,
            "received_date": self.received_date.isoformat() if self.received_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
