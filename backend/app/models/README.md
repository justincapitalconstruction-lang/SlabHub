# SlabHub Database Models

Comprehensive SQLAlchemy 2.0 models for the SlabHub inventory management system.

## Overview

The SlabHub database schema consists of four primary models:

1. **Slab** - Stone slab inventory tracking
2. **InventoryItem** - General inventory items (supplies, tools, etc.)
3. **Shipment** - Incoming shipment tracking
4. **ImportLog** - Data import operation logging

## File Structure

```
backend/app/models/
├── __init__.py         # Exports all models and utilities
├── base.py             # Database engine, session, and base configuration
├── slab.py             # Slab model for stone inventory
├── inventory.py        # InventoryItem and Shipment models
├── import_log.py       # ImportLog model for tracking imports
└── README.md           # This file
```

## Database Configuration

### SQLAlchemy Engine Setup

The database is configured in `base.py` with SQLite-specific optimizations:

- **check_same_thread=False** - Required for SQLite with multiple threads
- **StaticPool** - Optimized for SQLite single-file database
- **Foreign key constraints** - Automatically enabled for SQLite
- **Echo mode** - SQL query logging when debug=True

### Database URL

Configured via environment variable or defaults to:
```
sqlite:///./data/slabhub.db
```

## Models

### 1. Slab Model (`slab.py`)

Tracks individual stone slabs with comprehensive attributes.

**Key Features:**
- Public ID for QR codes and external references
- Detailed physical properties (stone type, finish, thickness, dimensions)
- Location and status tracking
- Image management (primary + additional images)
- Pricing (cost and selling price)
- Import tracking and batch management
- Perceptual hash for duplicate detection
- Flexible JSON storage for unmapped import fields

**Indexes:**
- `public_id` (unique)
- `name`, `stone_type`, `supplier`, `location`, `status`, `perceptual_hash`
- Composite: `(status, location)`, `(supplier, stone_type)`, `import_batch_id`

**Example Usage:**
```python
from backend.app.models import Slab, SessionLocal

db = SessionLocal()

# Create a new slab
slab = Slab(
    public_id="SLAB-ABC123",
    name="Calacatta Gold",
    stone_type="Marble",
    supplier="Stone Imports Inc",
    finish="Polished",
    thickness=3.0,
    length=120.0,
    width=75.0,
    square_feet=62.5,
    location="Warehouse A",
    status="available",
    cost=2500.00,
    price=4500.00
)

db.add(slab)
db.commit()
db.refresh(slab)

# Query slabs
available_slabs = db.query(Slab).filter(
    Slab.status == "available",
    Slab.location == "Warehouse A"
).all()

db.close()
```

### 2. InventoryItem Model (`inventory.py`)

Manages general inventory items (adhesives, sealers, tools, supplies).

**Key Features:**
- SKU-based tracking (unique identifier)
- Quantity management (on-hand, reserved, available)
- Reorder point alerts
- Category and location tracking
- Unit of measure flexibility
- Cost and pricing per unit

**Indexes:**
- `sku` (unique)
- `name`, `category`, `location`
- Composite: `(category, location)`

**Example Usage:**
```python
from backend.app.models import InventoryItem, SessionLocal

db = SessionLocal()

# Create inventory item
item = InventoryItem(
    sku="ADH-001",
    name="Premium Stone Adhesive",
    category="Adhesive",
    unit="Gallon",
    qty_on_hand=25,
    qty_reserved=5,
    reorder_point=10,
    unit_cost=45.00,
    unit_price=75.00
)

db.add(item)
db.commit()

# Check available quantity
available = item.qty_on_hand - item.qty_reserved  # 20

# Find items needing reorder
low_stock = db.query(InventoryItem).filter(
    InventoryItem.qty_on_hand <= InventoryItem.reorder_point
).all()

db.close()
```

### 3. Shipment Model (`inventory.py`)

Tracks incoming shipments from suppliers.

**Key Features:**
- Tracking number and PO number
- Supplier information
- Status tracking (pending, in_transit, received, etc.)
- Items stored as JSON array
- Important date tracking (ordered, expected, received)

**Indexes:**
- `tracking_number`, `po_number`, `supplier`, `status`
- `expected_date`
- Composite: `(supplier, status)`

**Example Usage:**
```python
from backend.app.models import Shipment, SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()

# Create shipment
shipment = Shipment(
    tracking_number="1Z999AA10123456784",
    supplier="Stone Imports Inc",
    po_number="PO-2026-001",
    status="in_transit",
    items=[
        {"sku": "SLAB-001", "quantity": 5},
        {"sku": "SLAB-002", "quantity": 3}
    ],
    ordered_date=datetime.now(),
    expected_date=datetime.now() + timedelta(days=7)
)

db.add(shipment)
db.commit()

# Find shipments expected this week
upcoming = db.query(Shipment).filter(
    Shipment.expected_date <= datetime.now() + timedelta(days=7),
    Shipment.status == "in_transit"
).all()

db.close()
```

### 4. ImportLog Model (`import_log.py`)

Logs all data import operations for audit and troubleshooting.

**Key Features:**
- Unique batch ID for each import
- Import type tracking (excel, csv, api, etc.)
- Comprehensive statistics (processed, success, failed, skipped)
- Error and warning arrays (JSON)
- Timing information (start and completion timestamps)
- Helper methods for duration and success rate calculation

**Indexes:**
- `batch_id` (unique)
- `import_type`, `status`
- `started_at`
- Composite: `(import_type, status)`

**Example Usage:**
```python
from backend.app.models import ImportLog, SessionLocal
from datetime import datetime
import uuid

db = SessionLocal()

# Create import log
import_log = ImportLog(
    batch_id=str(uuid.uuid4()),
    import_type="excel",
    source_path="/imports/slabs_2026_01.xlsx",
    status="running",
    items_processed=0,
    items_success=0,
    items_failed=0,
    items_skipped=0
)

db.add(import_log)
db.commit()

# Update during import
import_log.items_processed = 100
import_log.items_success = 95
import_log.items_failed = 5
import_log.status = "completed"
import_log.completed_at = datetime.now()
import_log.errors = [
    {"row": 45, "error": "Missing name"},
    {"row": 67, "error": "Invalid image"}
]

db.commit()

# Calculate metrics
success_rate = import_log.get_success_rate()  # 95.0%
duration = import_log.get_duration_seconds()  # e.g., 330.5

db.close()
```

## Database Initialization

### Method 1: Using init_db()

```python
from backend.app.models import init_db

# Initialize database (creates all tables)
init_db()
```

### Method 2: Standalone Script

```python
from backend.app.models.base import Base, engine

# Create all tables
Base.metadata.create_all(bind=engine)
```

### Method 3: Using the Test Script

```bash
python test_models.py
```

## Session Management

### Using get_db() Dependency (FastAPI)

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.app.models import get_db, Slab

@app.get("/slabs/")
def list_slabs(db: Session = Depends(get_db)):
    slabs = db.query(Slab).all()
    return slabs
```

### Manual Session Management

```python
from backend.app.models import SessionLocal

db = SessionLocal()
try:
    # Your database operations
    slabs = db.query(Slab).all()
    db.commit()
finally:
    db.close()
```

## Advanced Features

### JSON Fields

Several models use JSON fields for flexible data storage:

- **Slab.additional_images** - Array of image paths
- **Slab.extra_json** - Unmapped import fields
- **InventoryItem.images** - Product images
- **Shipment.items** - Array of shipment items
- **ImportLog.errors** - Error details
- **ImportLog.warnings** - Warning messages

**Example:**
```python
slab.additional_images = ["img1.jpg", "img2.jpg", "img3.jpg"]
slab.extra_json = {
    "grade": "A+",
    "origin": "Italy",
    "quarry": "Carrara Mountains"
}
db.commit()
```

### Timestamps

All models include automatic timestamps:

- **created_at** - Set automatically on creation (server_default=func.now())
- **updated_at** - Updated automatically on modification (onupdate=func.now())

These use `server_default` to ensure consistent timing regardless of application timezone.

### Model Serialization

All models include a `to_dict()` method for JSON serialization:

```python
slab = db.query(Slab).first()
slab_dict = slab.to_dict()
# Returns dictionary with all fields, ready for JSON response
```

## Indexes and Performance

All models include strategic indexes for common query patterns:

1. **Single-column indexes** on frequently filtered fields
2. **Composite indexes** for common multi-column queries
3. **Unique indexes** for identifier fields

This ensures optimal query performance for:
- Status-based filtering
- Location lookups
- Supplier/category searches
- Date range queries
- Import batch tracking

## Migration Considerations

When modifying models:

1. **SQLite Limitations** - Limited ALTER TABLE support
2. **Use Alembic** for production migrations
3. **Test migrations** on development database first
4. **Backup data** before schema changes

## Database URL Examples

```python
# SQLite (default)
DATABASE_URL = "sqlite:///./data/slabhub.db"

# PostgreSQL
DATABASE_URL = "postgresql://user:password@localhost/slabhub"

# MySQL
DATABASE_URL = "mysql+pymysql://user:password@localhost/slabhub"
```

## Testing

Run the included test script to verify models:

```bash
python test_models.py
```

This will:
1. Initialize the database
2. Create sample records for each model
3. Test queries and relationships
4. Verify serialization methods
5. Calculate metrics

## Best Practices

1. **Always use sessions properly** - Close sessions or use context managers
2. **Use indexes** - Leverage existing indexes for queries
3. **Batch operations** - Use bulk inserts for large datasets
4. **Validate data** - Check constraints before committing
5. **Handle errors** - Wrap operations in try/except blocks
6. **Use transactions** - Commit or rollback as appropriate

## Troubleshooting

### Common Issues

**"No module named 'pydantic_settings'"**
```bash
pip install pydantic-settings
```

**"No such table: slabs"**
```python
from backend.app.models import init_db
init_db()
```

**"Database is locked" (SQLite)**
- Check that check_same_thread=False is set
- Ensure sessions are properly closed
- Consider connection pooling

**"Foreign key constraint failed"**
- Foreign keys are enforced in SQLite (via pragma)
- Ensure referenced records exist before creating relationships

## Additional Resources

- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [FastAPI Database Tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
