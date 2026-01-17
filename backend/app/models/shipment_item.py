"""ShipmentItem model linking shipments to slabs."""
from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime

from .base import Base


class ShipmentItem(Base):
    """Represents an item within a shipment, linking a shipment to a specific slab."""
    __tablename__ = "shipment_items"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    slab_id = Column(Integer, ForeignKey("slabs.id"), nullable=False)
    quantity = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
