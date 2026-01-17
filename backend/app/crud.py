"""
CRUD operations for SlabHub
Database access layer for slabs, inventory items, and shipments
"""
import logging
import uuid
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func

from backend.app.models import Slab, InventoryItem, Shipment
from backend.app.schemas import (
    SlabCreate,
    SlabUpdate,
    InventoryItemCreate,
    InventoryItemUpdate,
    ShipmentCreate,
    ShipmentUpdate,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Slab CRUD Operations
# ============================================================================

def get_slab(db: Session, slab_id: int) -> Optional[Slab]:
    """
    Get a single slab by ID.

    Args:
        db: Database session
        slab_id: Slab ID

    Returns:
        Slab model instance or None if not found
    """
    try:
        return db.query(Slab).filter(Slab.id == slab_id).first()
    except Exception as e:
        logger.error(f"Error getting slab {slab_id}: {e}", exc_info=True)
        return None


def get_slab_by_public_id(db: Session, public_id: str) -> Optional[Slab]:
    """
    Get a single slab by public ID.

    Args:
        db: Database session
        public_id: Public identifier for QR codes

    Returns:
        Slab model instance or None if not found
    """
    try:
        return db.query(Slab).filter(Slab.public_id == public_id).first()
    except Exception as e:
        logger.error(f"Error getting slab by public_id {public_id}: {e}", exc_info=True)
        return None


def get_slabs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> tuple[List[Slab], int]:
    """
    Get a list of slabs with optional filtering and pagination.

    Args:
        db: Database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        filters: Dictionary of filter criteria:
            - search: str - Search in name, stone_type, supplier
            - stone_type: str - Filter by stone type
            - supplier: str - Filter by supplier
            - location: str - Filter by location
            - status: str - Filter by status

    Returns:
        Tuple of (list of Slab instances, total count)
    """
    try:
        query = db.query(Slab)

        # Apply filters if provided
        if filters:
            # Search filter (searches across multiple fields)
            if search := filters.get("search"):
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        Slab.name.ilike(search_term),
                        Slab.stone_type.ilike(search_term),
                        Slab.supplier.ilike(search_term),
                        Slab.color.ilike(search_term),
                        Slab.location.ilike(search_term),
                        Slab.public_id.ilike(search_term),
                    )
                )

            # Exact match filters
            if stone_type := filters.get("stone_type"):
                query = query.filter(Slab.stone_type == stone_type)

            if supplier := filters.get("supplier"):
                query = query.filter(Slab.supplier == supplier)

            if location := filters.get("location"):
                query = query.filter(Slab.location == location)

            if status := filters.get("status"):
                query = query.filter(Slab.status == status)

        # Get total count before pagination
        total = query.count()

        # Apply ordering (most recent first)
        query = query.order_by(Slab.created_at.desc())

        # Apply pagination
        slabs = query.offset(skip).limit(limit).all()

        logger.debug(f"Retrieved {len(slabs)} slabs (total: {total})")
        return slabs, total

    except Exception as e:
        logger.error(f"Error getting slabs: {e}", exc_info=True)
        return [], 0


def create_slab(db: Session, slab_data: SlabCreate) -> Optional[Slab]:
    """
    Create a new slab.

    Args:
        db: Database session
        slab_data: Slab creation data

    Returns:
        Created Slab instance or None if failed
    """
    try:
        # Generate unique public_id
        public_id = _generate_unique_public_id(db)

        # Create slab instance
        slab = Slab(
            public_id=public_id,
            **slab_data.model_dump()
        )

        db.add(slab)
        db.commit()
        db.refresh(slab)

        logger.info(f"Created slab: {slab.public_id} (ID: {slab.id})")
        return slab

    except Exception as e:
        # Roll back and re-raise unexpected errors so the caller can return a 500
        logger.error(f"Error creating slab: {e}", exc_info=True)
        db.rollback()
        raise


def update_slab(
    db: Session,
    slab_id: int,
    slab_data: SlabUpdate
) -> Optional[Slab]:
    """
    Update an existing slab.

    Args:
        db: Database session
        slab_id: Slab ID to update
        slab_data: Slab update data (only provided fields will be updated)

    Returns:
        Updated Slab instance or None if not found or failed
    """
    try:
        slab = get_slab(db, slab_id)
        if not slab:
            logger.warning(f"Slab {slab_id} not found for update")
            return None

        # Update only provided fields
        update_data = slab_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(slab, field, value)

        db.commit()
        db.refresh(slab)

        logger.info(f"Updated slab: {slab.public_id} (ID: {slab.id})")
        return slab

    except Exception as e:
        # Roll back and re‑raise to allow callers to handle server errors separately
        logger.error(f"Error updating slab {slab_id}: {e}", exc_info=True)
        db.rollback()
        raise


def delete_slab(db: Session, slab_id: int) -> bool:
    """
    Delete a slab.

    Args:
        db: Database session
        slab_id: Slab ID to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        slab = get_slab(db, slab_id)
        if not slab:
            logger.warning(f"Slab {slab_id} not found for deletion")
            return False

        public_id = slab.public_id
        db.delete(slab)
        db.commit()

        logger.info(f"Deleted slab: {public_id} (ID: {slab_id})")
        return True

    except Exception as e:
        logger.error(f"Error deleting slab {slab_id}: {e}", exc_info=True)
        db.rollback()
        raise


def search_slabs(db: Session, query: str, limit: int = 50) -> List[Slab]:
    """
    Full-text search for slabs.

    Searches across name, stone_type, supplier, color, location, and tags.

    Args:
        db: Database session
        query: Search query string
        limit: Maximum number of results

    Returns:
        List of matching Slab instances
    """
    try:
        search_term = f"%{query}%"

        slabs = db.query(Slab).filter(
            or_(
                Slab.name.ilike(search_term),
                Slab.stone_type.ilike(search_term),
                Slab.supplier.ilike(search_term),
                Slab.color.ilike(search_term),
                Slab.location.ilike(search_term),
                Slab.tags.ilike(search_term),
                Slab.public_id.ilike(search_term),
            )
        ).order_by(Slab.created_at.desc()).limit(limit).all()

        logger.debug(f"Search for '{query}' returned {len(slabs)} results")
        return slabs

    except Exception as e:
        logger.error(f"Error searching slabs with query '{query}': {e}", exc_info=True)
        return []


# ============================================================================
# Inventory Item CRUD Operations
# ============================================================================

def get_inventory_item(db: Session, item_id: int) -> Optional[InventoryItem]:
    """
    Get a single inventory item by ID.

    Args:
        db: Database session
        item_id: Inventory item ID

    Returns:
        InventoryItem model instance or None if not found
    """
    try:
        return db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    except Exception as e:
        logger.error(f"Error getting inventory item {item_id}: {e}", exc_info=True)
        return None


def get_inventory_item_by_sku(db: Session, sku: str) -> Optional[InventoryItem]:
    """
    Get a single inventory item by SKU.

    Args:
        db: Database session
        sku: Stock keeping unit

    Returns:
        InventoryItem model instance or None if not found
    """
    try:
        return db.query(InventoryItem).filter(InventoryItem.sku == sku).first()
    except Exception as e:
        logger.error(f"Error getting inventory item by SKU {sku}: {e}", exc_info=True)
        return None


def get_inventory_items(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> tuple[List[InventoryItem], int]:
    """
    Get a list of inventory items with optional filtering and pagination.

    Args:
        db: Database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        filters: Dictionary of filter criteria:
            - search: str - Search in name, sku, description
            - category: str - Filter by category
            - location: str - Filter by location
            - low_stock: bool - Show only items at or below reorder point

    Returns:
        Tuple of (list of InventoryItem instances, total count)
    """
    try:
        query = db.query(InventoryItem)

        # Apply filters if provided
        if filters:
            # Search filter
            if search := filters.get("search"):
                search_term = f"%{search}%"
                query = query.filter(
                    or_(
                        InventoryItem.name.ilike(search_term),
                        InventoryItem.sku.ilike(search_term),
                        InventoryItem.description.ilike(search_term),
                    )
                )

            # Exact match filters
            if category := filters.get("category"):
                query = query.filter(InventoryItem.category == category)

            if location := filters.get("location"):
                query = query.filter(InventoryItem.location == location)

            # Low stock filter
            if filters.get("low_stock"):
                query = query.filter(
                    and_(
                        InventoryItem.reorder_point.isnot(None),
                        InventoryItem.qty_on_hand <= InventoryItem.reorder_point
                    )
                )

        # Get total count before pagination
        total = query.count()

        # Apply ordering (alphabetical by name)
        query = query.order_by(InventoryItem.name)

        # Apply pagination
        items = query.offset(skip).limit(limit).all()

        logger.debug(f"Retrieved {len(items)} inventory items (total: {total})")
        return items, total

    except Exception as e:
        logger.error(f"Error getting inventory items: {e}", exc_info=True)
        return [], 0


def create_inventory_item(
    db: Session,
    item_data: InventoryItemCreate
) -> Optional[InventoryItem]:
    """
    Create a new inventory item.

    Args:
        db: Database session
        item_data: Inventory item creation data

    Returns:
        Created InventoryItem instance or None if failed
    """
    try:
        # Check if SKU already exists
        existing = get_inventory_item_by_sku(db, item_data.sku)
        if existing:
            logger.warning(f"SKU {item_data.sku} already exists")
            return None

        # Create item instance
        item = InventoryItem(**item_data.model_dump())

        db.add(item)
        db.commit()
        db.refresh(item)

        logger.info(f"Created inventory item: {item.sku} (ID: {item.id})")
        return item

    except Exception as e:
        logger.error(f"Error creating inventory item: {e}", exc_info=True)
        db.rollback()
        raise


def update_inventory_item(
    db: Session,
    item_id: int,
    item_data: InventoryItemUpdate
) -> Optional[InventoryItem]:
    """
    Update an existing inventory item.

    Args:
        db: Database session
        item_id: Inventory item ID to update
        item_data: Inventory item update data (only provided fields will be updated)

    Returns:
        Updated InventoryItem instance or None if not found or failed
    """
    try:
        item = get_inventory_item(db, item_id)
        if not item:
            logger.warning(f"Inventory item {item_id} not found for update")
            return None

        # Update only provided fields
        update_data = item_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)

        db.commit()
        db.refresh(item)

        logger.info(f"Updated inventory item: {item.sku} (ID: {item.id})")
        return item

    except Exception as e:
        logger.error(f"Error updating inventory item {item_id}: {e}", exc_info=True)
        db.rollback()
        raise


def delete_inventory_item(db: Session, item_id: int) -> bool:
    """
    Delete an inventory item.

    Args:
        db: Database session
        item_id: Inventory item ID to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        item = get_inventory_item(db, item_id)
        if not item:
            logger.warning(f"Inventory item {item_id} not found for deletion")
            return False

        sku = item.sku
        db.delete(item)
        db.commit()

        logger.info(f"Deleted inventory item: {sku} (ID: {item_id})")
        return True

    except Exception as e:
        logger.error(f"Error deleting inventory item {item_id}: {e}", exc_info=True)
        db.rollback()
        raise


# ============================================================================
# Shipment CRUD Operations
# ============================================================================

def get_shipment(db: Session, shipment_id: int) -> Optional[Shipment]:
    """
    Get a single shipment by ID.

    Args:
        db: Database session
        shipment_id: Shipment ID

    Returns:
        Shipment model instance or None if not found
    """
    try:
        return db.query(Shipment).filter(Shipment.id == shipment_id).first()
    except Exception as e:
        logger.error(f"Error getting shipment {shipment_id}: {e}", exc_info=True)
        return None


def get_shipments(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> tuple[List[Shipment], int]:
    """
    Get a list of shipments with optional filtering and pagination.

    Args:
        db: Database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        filters: Dictionary of filter criteria:
            - supplier: str - Filter by supplier
            - status: str - Filter by status
            - tracking_number: str - Filter by tracking number

    Returns:
        Tuple of (list of Shipment instances, total count)
    """
    try:
        query = db.query(Shipment)

        # Apply filters if provided
        if filters:
            if supplier := filters.get("supplier"):
                query = query.filter(Shipment.supplier == supplier)

            if status := filters.get("status"):
                query = query.filter(Shipment.status == status)

            if tracking_number := filters.get("tracking_number"):
                query = query.filter(Shipment.tracking_number == tracking_number)

        # Get total count before pagination
        total = query.count()

        # Apply ordering (most recent expected date first)
        query = query.order_by(Shipment.expected_date.desc().nullslast())

        # Apply pagination
        shipments = query.offset(skip).limit(limit).all()

        logger.debug(f"Retrieved {len(shipments)} shipments (total: {total})")
        return shipments, total

    except Exception as e:
        logger.error(f"Error getting shipments: {e}", exc_info=True)
        return [], 0


def create_shipment(db: Session, shipment_data: ShipmentCreate) -> Optional[Shipment]:
    """
    Create a new shipment.

    Args:
        db: Database session
        shipment_data: Shipment creation data

    Returns:
        Created Shipment instance or None if failed
    """
    try:
        shipment = Shipment(**shipment_data.model_dump())

        db.add(shipment)
        db.commit()
        db.refresh(shipment)

        logger.info(f"Created shipment: {shipment.supplier} (ID: {shipment.id})")
        return shipment

    except Exception as e:
        logger.error(f"Error creating shipment: {e}", exc_info=True)
        db.rollback()
        raise


def update_shipment(
    db: Session,
    shipment_id: int,
    shipment_data: ShipmentUpdate
) -> Optional[Shipment]:
    """
    Update an existing shipment.

    Args:
        db: Database session
        shipment_id: Shipment ID to update
        shipment_data: Shipment update data (only provided fields will be updated)

    Returns:
        Updated Shipment instance or None if not found or failed
    """
    try:
        shipment = get_shipment(db, shipment_id)
        if not shipment:
            logger.warning(f"Shipment {shipment_id} not found for update")
            return None

        # Update only provided fields
        update_data = shipment_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(shipment, field, value)

        db.commit()
        db.refresh(shipment)

        logger.info(f"Updated shipment: {shipment.supplier} (ID: {shipment.id})")
        return shipment

    except Exception as e:
        logger.error(f"Error updating shipment {shipment_id}: {e}", exc_info=True)
        db.rollback()
        raise


def delete_shipment(db: Session, shipment_id: int) -> bool:
    """
    Delete a shipment.

    Args:
        db: Database session
        shipment_id: Shipment ID to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        shipment = get_shipment(db, shipment_id)
        if not shipment:
            logger.warning(f"Shipment {shipment_id} not found for deletion")
            return False

        db.delete(shipment)
        db.commit()

        logger.info(f"Deleted shipment (ID: {shipment_id})")
        return True

    except Exception as e:
        logger.error(f"Error deleting shipment {shipment_id}: {e}", exc_info=True)
        db.rollback()
        raise


# ============================================================================
# Helper Functions
# ============================================================================

def _generate_unique_public_id(db: Session, length: int = 8) -> str:
    """
    Generate a unique public ID for a slab.

    Args:
        db: Database session
        length: Length of the public ID (default: 8)

    Returns:
        Unique public ID string
    """
    max_attempts = 100
    for _ in range(max_attempts):
        # Generate random ID
        public_id = str(uuid.uuid4())[:length].upper()

        # Check if it already exists
        existing = get_slab_by_public_id(db, public_id)
        if not existing:
            return public_id

    # Fallback to longer UUID if we can't find a unique short ID
    logger.warning("Failed to generate short unique public_id, using full UUID")
    return str(uuid.uuid4())
