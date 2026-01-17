"""SlabImage model for storing multiple images per slab."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey

from .base import Base


class SlabImage(Base):
    """Represents an additional image associated with a slab."""
    __tablename__ = "slab_images"

    id = Column(Integer, primary_key=True, index=True)
    slab_id = Column(Integer, ForeignKey("slabs.id"), nullable=False)
    image_path = Column(String(500), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
