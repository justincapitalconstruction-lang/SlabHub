"""
Test script to verify SQLAlchemy models work correctly
Run this to initialize the database and test model creation
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.models import init_db, SessionLocal, Slab, InventoryItem, Shipment, ImportLog
from datetime import datetime
import uuid


def test_database_initialization():
    """Test database initialization"""
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
    print()


def test_slab_model():
    """Test Slab model creation"""
    print("Testing Slab model...")
    db = SessionLocal()

    try:
        # Create a test slab
        slab = Slab(
            public_id=f"SLAB-{uuid.uuid4().hex[:8].upper()}",
            name="Calacatta Gold Premium",
            stone_type="Marble",
            supplier="Stone Imports Inc",
            finish="Polished",
            thickness=3.0,
            color="White with gold veining",
            length=120.0,
            width=75.0,
            square_feet=62.5,
            location="Warehouse A, Row 3",
            status="available",
            quantity=1,
            tags="premium,marble,white,calacatta",
            notes="Beautiful premium slab with distinctive gold veining",
            cost=2500.00,
            price=4500.00,
            additional_images=["img1.jpg", "img2.jpg"],
            extra_json={"grade": "A+", "origin": "Italy"}
        )

        db.add(slab)
        db.commit()
        db.refresh(slab)

        print(f"Created slab: {slab}")
        print(f"Slab dict: {slab.to_dict()}")
        print()

        return slab.id
    finally:
        db.close()


def test_inventory_item_model():
    """Test InventoryItem model creation"""
    print("Testing InventoryItem model...")
    db = SessionLocal()

    try:
        # Create a test inventory item
        item = InventoryItem(
            sku="ADH-001",
            name="Premium Stone Adhesive",
            description="Professional-grade adhesive for stone installation",
            category="Adhesive",
            unit="Gallon",
            qty_on_hand=25,
            qty_reserved=5,
            reorder_point=10,
            location="Supply Room A",
            unit_cost=45.00,
            unit_price=75.00,
            tags="adhesive,installation,professional",
            images=["product1.jpg", "product2.jpg"]
        )

        db.add(item)
        db.commit()
        db.refresh(item)

        print(f"Created inventory item: {item}")
        print(f"Available quantity: {item.qty_on_hand - item.qty_reserved}")
        print()

        return item.id
    finally:
        db.close()


def test_shipment_model():
    """Test Shipment model creation"""
    print("Testing Shipment model...")
    db = SessionLocal()

    try:
        # Create a test shipment
        shipment = Shipment(
            tracking_number="1Z999AA10123456784",
            supplier="Stone Imports Inc",
            po_number="PO-2026-001",
            status="in_transit",
            items=[
                {"sku": "SLAB-MAR-001", "quantity": 5, "description": "Carrara Marble Slabs"},
                {"sku": "SLAB-GRA-003", "quantity": 3, "description": "Black Galaxy Granite"}
            ],
            notes="Fragile - Handle with care",
            ordered_date=datetime(2026, 1, 5),
            expected_date=datetime(2026, 1, 15)
        )

        db.add(shipment)
        db.commit()
        db.refresh(shipment)

        print(f"Created shipment: {shipment}")
        print(f"Shipment dict: {shipment.to_dict()}")
        print()

        return shipment.id
    finally:
        db.close()


def test_import_log_model():
    """Test ImportLog model creation"""
    print("Testing ImportLog model...")
    db = SessionLocal()

    try:
        # Create a test import log
        import_log = ImportLog(
            batch_id=str(uuid.uuid4()),
            import_type="excel",
            source_path="C:/imports/slabs_2026_01.xlsx",
            status="completed",
            items_processed=100,
            items_success=95,
            items_failed=2,
            items_skipped=3,
            errors=[
                {"row": 45, "error": "Missing required field: name"},
                {"row": 67, "error": "Invalid image path"}
            ],
            warnings=[
                {"row": 12, "warning": "Supplier not in database"},
                {"row": 23, "warning": "Unusual thickness value"},
                {"row": 89, "warning": "Missing cost information"}
            ],
            summary="Successfully imported 95 slabs from Excel spreadsheet",
            started_at=datetime(2026, 1, 10, 10, 0, 0),
            completed_at=datetime(2026, 1, 10, 10, 5, 30)
        )

        db.add(import_log)
        db.commit()
        db.refresh(import_log)

        print(f"Created import log: {import_log}")
        print(f"Success rate: {import_log.get_success_rate():.1f}%")
        print(f"Duration: {import_log.get_duration_seconds()} seconds")
        print()

        return import_log.id
    finally:
        db.close()


def query_models():
    """Test querying models"""
    print("Testing model queries...")
    db = SessionLocal()

    try:
        # Query slabs
        slabs = db.query(Slab).filter(Slab.status == "available").all()
        print(f"Found {len(slabs)} available slabs")

        # Query inventory items with low stock
        low_stock = db.query(InventoryItem).filter(
            InventoryItem.qty_on_hand <= InventoryItem.reorder_point
        ).all()
        print(f"Found {len(low_stock)} items with low stock")

        # Query recent import logs
        recent_imports = db.query(ImportLog).order_by(
            ImportLog.started_at.desc()
        ).limit(5).all()
        print(f"Found {len(recent_imports)} recent imports")

        # Query in-transit shipments
        in_transit = db.query(Shipment).filter(
            Shipment.status == "in_transit"
        ).all()
        print(f"Found {len(in_transit)} shipments in transit")

        print()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("SlabHub Database Models Test")
    print("=" * 60)
    print()

    try:
        test_database_initialization()
        test_slab_model()
        test_inventory_item_model()
        test_shipment_model()
        test_import_log_model()
        query_models()

        print("=" * 60)
        print("All tests passed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
