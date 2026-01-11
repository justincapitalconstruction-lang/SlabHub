# SlabHub Database Schema

## Overview

Production-ready SQLAlchemy 2.0 models for comprehensive inventory management.

## Schema Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                            SLABS                                 │
├─────────────────────────────────────────────────────────────────┤
│ PK  id (Integer)                                                 │
│ UQ  public_id (String 50) ────────────── QR Code Reference       │
│ IDX name (String 255)                                            │
│ IDX stone_type (String 100)                                      │
│ IDX supplier (String 200)                                        │
│     finish (String 50)                                           │
│     thickness (Float)                                            │
│     color (String 100)                                           │
│     length, width, square_feet (Float)                           │
│ IDX location (String 100)                                        │
│ IDX status (String 50) ──────────────── default: 'available'     │
│     quantity (Integer) ──────────────── default: 1               │
│     tags (Text)                                                  │
│     notes (Text)                                                 │
│     primary_image (String 500)                                   │
│     additional_images (JSON) ────────── Array of image paths     │
│     extra_json (JSON) ───────────────── Unmapped import fields   │
│     cost, price (Float)                                          │
│     created_at (DateTime) ───────────── auto: func.now()         │
│     updated_at (DateTime) ───────────── auto: func.now()         │
│     import_source (String 100)                                   │
│ IDX import_batch_id (String 100)                                 │
│ IDX perceptual_hash (String 64) ─────── Duplicate detection      │
│     qr_code_path (String 500)                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                       INVENTORY_ITEMS                            │
├─────────────────────────────────────────────────────────────────┤
│ PK  id (Integer)                                                 │
│ UQ  sku (String 100) ────────────────── Unique identifier        │
│ IDX name (String 255)                                            │
│     description (Text)                                           │
│ IDX category (String 100)                                        │
│     unit (String 50) ────────────────── Unit of measure          │
│     qty_on_hand (Integer) ───────────── default: 0               │
│     qty_reserved (Integer) ──────────── default: 0               │
│     reorder_point (Integer)                                      │
│ IDX location (String 100)                                        │
│     unit_cost, unit_price (Float)                                │
│     tags (Text)                                                  │
│     notes (Text)                                                 │
│     images (JSON) ───────────────────── Array of image paths     │
│     created_at (DateTime) ───────────── auto: func.now()         │
│     updated_at (DateTime) ───────────── auto: func.now()         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                          SHIPMENTS                               │
├─────────────────────────────────────────────────────────────────┤
│ PK  id (Integer)                                                 │
│ IDX tracking_number (String 100)                                 │
│ IDX supplier (String 200)                                        │
│ IDX po_number (String 100) ──────────── Purchase order #         │
│ IDX status (String 50) ──────────────── default: 'pending'       │
│     items (JSON) ────────────────────── Array of shipment items  │
│     notes (Text)                                                 │
│     ordered_date (DateTime)                                      │
│ IDX expected_date (DateTime)                                     │
│     received_date (DateTime)                                     │
│     created_at (DateTime) ───────────── auto: func.now()         │
│     updated_at (DateTime) ───────────── auto: func.now()         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        IMPORT_LOGS                               │
├─────────────────────────────────────────────────────────────────┤
│ PK  id (Integer)                                                 │
│ UQ  batch_id (String 100) ───────────── Unique batch UUID        │
│ IDX import_type (String 50) ─────────── excel, csv, api, etc.    │
│     source_path (String 500)                                     │
│ IDX status (String 50) ──────────────── default: 'running'       │
│     items_processed (Integer) ───────── default: 0               │
│     items_success (Integer) ─────────── default: 0               │
│     items_failed (Integer) ──────────── default: 0               │
│     items_skipped (Integer) ─────────── default: 0               │
│     errors (JSON) ───────────────────── Array of error objects   │
│     warnings (JSON) ─────────────────── Array of warning objects │
│     summary (Text)                                               │
│ IDX started_at (DateTime) ───────────── auto: func.now()         │
│     completed_at (DateTime)                                      │
│     created_at (DateTime) ───────────── auto: func.now()         │
│     updated_at (DateTime) ───────────── auto: func.now()         │
└─────────────────────────────────────────────────────────────────┘
```

## Composite Indexes

### Slabs
- `idx_slab_status_location` → (status, location)
- `idx_slab_supplier_stone_type` → (supplier, stone_type)
- `idx_slab_import_batch` → (import_batch_id)

### Inventory Items
- `idx_inventory_category_location` → (category, location)

### Shipments
- `idx_shipment_supplier_status` → (supplier, status)
- `idx_shipment_expected_date` → (expected_date)

### Import Logs
- `idx_import_type_status` → (import_type, status)
- `idx_import_started_at` → (started_at)

## Key Features

### 1. SQLAlchemy 2.0 Modern Syntax
- ✅ `Mapped[type]` type annotations
- ✅ `mapped_column()` configuration
- ✅ Server-side defaults with `func.now()`
- ✅ Automatic timestamp updates with `onupdate`

### 2. Production-Ready Features
- ✅ Comprehensive indexing strategy
- ✅ Unique constraints on identifiers
- ✅ JSON fields for flexible data
- ✅ Automatic timestamp management
- ✅ Foreign key enforcement (SQLite pragma)
- ✅ Connection pooling configuration

### 3. SQLite Optimizations
- ✅ `check_same_thread=False` for multi-threading
- ✅ `StaticPool` for single-file database
- ✅ Foreign key pragma enforcement
- ✅ Echo mode for debugging

### 4. Developer Experience
- ✅ `to_dict()` methods for JSON serialization
- ✅ Helper methods (get_duration_seconds, get_success_rate)
- ✅ Comprehensive `__repr__` methods
- ✅ FastAPI dependency injection support
- ✅ Type hints throughout

## Field Details

### Status Values

**Slab.status**
- `available` - Ready for sale
- `reserved` - Held for customer
- `sold` - Sold and invoiced
- `damaged` - Damaged, not sellable
- `archived` - Historical record

**Shipment.status**
- `pending` - Order placed, not shipped
- `in_transit` - Currently shipping
- `received` - Delivered and checked in
- `cancelled` - Order cancelled
- `delayed` - Expected date changed

**ImportLog.status**
- `running` - Import in progress
- `completed` - Successfully finished
- `failed` - Import failed
- `partial` - Some items failed

### JSON Field Structures

**Slab.additional_images**
```json
["path/to/image1.jpg", "path/to/image2.jpg", "path/to/image3.jpg"]
```

**Slab.extra_json**
```json
{
  "grade": "A+",
  "origin": "Italy",
  "quarry": "Carrara Mountains",
  "custom_field": "value"
}
```

**Shipment.items**
```json
[
  {
    "sku": "SLAB-001",
    "quantity": 5,
    "description": "Carrara Marble Slabs"
  },
  {
    "sku": "ADH-001",
    "quantity": 10,
    "description": "Stone Adhesive"
  }
]
```

**ImportLog.errors**
```json
[
  {
    "row": 45,
    "field": "name",
    "error": "Missing required field",
    "value": null
  },
  {
    "row": 67,
    "field": "primary_image",
    "error": "File not found",
    "value": "missing.jpg"
  }
]
```

## Usage Examples

### Initialize Database
```python
from backend.app.models import init_db
init_db()
```

### Query Available Slabs by Location
```python
from backend.app.models import Slab, SessionLocal

db = SessionLocal()
slabs = db.query(Slab).filter(
    Slab.status == "available",
    Slab.location == "Warehouse A"
).order_by(Slab.created_at.desc()).all()
db.close()
```

### Check Low Stock Items
```python
from backend.app.models import InventoryItem, SessionLocal

db = SessionLocal()
low_stock = db.query(InventoryItem).filter(
    InventoryItem.qty_on_hand <= InventoryItem.reorder_point
).all()
db.close()
```

### Track Import Progress
```python
from backend.app.models import ImportLog, SessionLocal

db = SessionLocal()
recent_imports = db.query(ImportLog).filter(
    ImportLog.status == "completed"
).order_by(ImportLog.started_at.desc()).limit(10).all()

for log in recent_imports:
    print(f"Batch: {log.batch_id}")
    print(f"Success Rate: {log.get_success_rate():.1f}%")
    print(f"Duration: {log.get_duration_seconds():.1f}s")
db.close()
```

## Files Created

```
backend/app/models/
├── __init__.py          (24 lines)   - Model exports
├── base.py              (80 lines)   - Database configuration
├── slab.py              (256 lines)  - Slab model
├── inventory.py         (297 lines)  - InventoryItem + Shipment models
├── import_log.py        (184 lines)  - ImportLog model
└── README.md            (11 KB)      - Comprehensive documentation

test_models.py           (235 lines)  - Complete test suite
DATABASE_SCHEMA.md       (This file)  - Schema reference
```

**Total:** 1,076 lines of production-ready code

## Migration Path

For future database migrations with Alembic:

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add new field"

# Apply migration
alembic upgrade head
```

## Performance Considerations

1. **Indexed Fields** - All frequently queried fields have indexes
2. **Composite Indexes** - Multi-column queries are optimized
3. **JSON Fields** - Use for flexible, semi-structured data
4. **Connection Pooling** - Configured for optimal performance
5. **Batch Operations** - Use bulk_insert_mappings for large imports

## Security Notes

1. **SQL Injection** - Protected by SQLAlchemy parameterization
2. **Data Validation** - Use Pydantic schemas for input validation
3. **Sensitive Data** - Store file paths, not actual files
4. **Audit Trail** - Automatic timestamps on all models
5. **Import Tracking** - Complete audit log of all imports

---

**Database Engine:** SQLite (development) / PostgreSQL (production ready)
**ORM Version:** SQLAlchemy 2.0+
**Python Version:** 3.10+
**Status:** Production Ready ✅
