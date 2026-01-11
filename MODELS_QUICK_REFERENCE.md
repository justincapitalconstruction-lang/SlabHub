# SlabHub Models - Quick Reference

## Import Models

```python
from backend.app.models import (
    # Database setup
    init_db,
    get_db,
    SessionLocal,

    # Models
    Slab,
    InventoryItem,
    Shipment,
    ImportLog
)
```

## Initialize Database

```python
from backend.app.models import init_db

# Create all tables
init_db()
```

## Common Operations

### Create a Slab

```python
from backend.app.models import Slab, SessionLocal
import uuid

db = SessionLocal()

slab = Slab(
    public_id=f"SLAB-{uuid.uuid4().hex[:8].upper()}",
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
db.close()
```

### Query Available Slabs

```python
from backend.app.models import Slab, SessionLocal

db = SessionLocal()

# Filter by status and location
slabs = db.query(Slab).filter(
    Slab.status == "available",
    Slab.location == "Warehouse A"
).all()

# Search by name
results = db.query(Slab).filter(
    Slab.name.ilike("%calacatta%")
).all()

# Get by public_id
slab = db.query(Slab).filter(
    Slab.public_id == "SLAB-ABC123"
).first()

db.close()
```

### Create Inventory Item

```python
from backend.app.models import InventoryItem, SessionLocal

db = SessionLocal()

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
db.close()
```

### Check Low Stock

```python
from backend.app.models import InventoryItem, SessionLocal

db = SessionLocal()

low_stock = db.query(InventoryItem).filter(
    InventoryItem.qty_on_hand <= InventoryItem.reorder_point
).all()

for item in low_stock:
    available = item.qty_on_hand - item.qty_reserved
    print(f"{item.name}: {available} available (reorder at {item.reorder_point})")

db.close()
```

### Track Shipment

```python
from backend.app.models import Shipment, SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()

shipment = Shipment(
    tracking_number="1Z999AA10123456784",
    supplier="Stone Imports Inc",
    po_number="PO-2026-001",
    status="in_transit",
    items=[
        {"sku": "SLAB-001", "quantity": 5, "description": "Carrara Marble"},
        {"sku": "SLAB-002", "quantity": 3, "description": "Black Galaxy Granite"}
    ],
    ordered_date=datetime.now(),
    expected_date=datetime.now() + timedelta(days=7)
)

db.add(shipment)
db.commit()
db.close()
```

### Log Import Operation

```python
from backend.app.models import ImportLog, SessionLocal
from datetime import datetime
import uuid

db = SessionLocal()

# Start import
import_log = ImportLog(
    batch_id=str(uuid.uuid4()),
    import_type="excel",
    source_path="/imports/slabs_2026_01.xlsx",
    status="running"
)
db.add(import_log)
db.commit()

# Update progress
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

# Get metrics
print(f"Success rate: {import_log.get_success_rate():.1f}%")
print(f"Duration: {import_log.get_duration_seconds():.1f}s")

db.close()
```

## FastAPI Integration

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from backend.app.models import get_db, Slab

app = FastAPI()

@app.get("/slabs/")
def list_slabs(
    status: str = "available",
    db: Session = Depends(get_db)
):
    slabs = db.query(Slab).filter(Slab.status == status).all()
    return [slab.to_dict() for slab in slabs]

@app.get("/slabs/{public_id}")
def get_slab(public_id: str, db: Session = Depends(get_db)):
    slab = db.query(Slab).filter(Slab.public_id == public_id).first()
    if not slab:
        return {"error": "Slab not found"}, 404
    return slab.to_dict()

@app.post("/slabs/")
def create_slab(slab_data: dict, db: Session = Depends(get_db)):
    slab = Slab(**slab_data)
    db.add(slab)
    db.commit()
    db.refresh(slab)
    return slab.to_dict()
```

## Model Serialization

```python
# All models have to_dict() method
slab = db.query(Slab).first()
slab_dict = slab.to_dict()

# Convert to JSON
import json
json_str = json.dumps(slab_dict, default=str)
```

## Common Queries

### Find Slabs by Import Batch

```python
slabs = db.query(Slab).filter(
    Slab.import_batch_id == "batch-123"
).all()
```

### Count Slabs by Status

```python
from sqlalchemy import func

status_counts = db.query(
    Slab.status,
    func.count(Slab.id)
).group_by(Slab.status).all()

# [('available', 150), ('sold', 45), ('reserved', 12)]
```

### Recent Import Logs

```python
recent = db.query(ImportLog).order_by(
    ImportLog.started_at.desc()
).limit(10).all()
```

### Shipments Expected This Week

```python
from datetime import datetime, timedelta

end_of_week = datetime.now() + timedelta(days=7)
shipments = db.query(Shipment).filter(
    Shipment.expected_date <= end_of_week,
    Shipment.status == "in_transit"
).all()
```

## Field Reference

### Slab Model
| Field | Type | Required | Indexed | Description |
|-------|------|----------|---------|-------------|
| id | Integer | Yes (PK) | Yes | Primary key |
| public_id | String(50) | Yes | Yes (Unique) | QR code ID |
| name | String(255) | Yes | Yes | Slab name |
| stone_type | String(100) | No | Yes | Granite, marble, etc. |
| supplier | String(200) | No | Yes | Supplier name |
| location | String(100) | No | Yes | Storage location |
| status | String(50) | Yes | Yes | available, sold, etc. |
| price | Float | No | No | Selling price |

### InventoryItem Model
| Field | Type | Required | Indexed | Description |
|-------|------|----------|---------|-------------|
| id | Integer | Yes (PK) | Yes | Primary key |
| sku | String(100) | Yes | Yes (Unique) | Stock keeping unit |
| name | String(255) | Yes | Yes | Item name |
| category | String(100) | No | Yes | Item category |
| qty_on_hand | Integer | Yes | No | Quantity in stock |
| qty_reserved | Integer | Yes | No | Reserved quantity |

### Shipment Model
| Field | Type | Required | Indexed | Description |
|-------|------|----------|---------|-------------|
| id | Integer | Yes (PK) | Yes | Primary key |
| tracking_number | String(100) | No | Yes | Carrier tracking |
| supplier | String(200) | Yes | Yes | Supplier name |
| status | String(50) | Yes | Yes | pending, in_transit, etc. |
| expected_date | DateTime | No | Yes | Expected delivery |

### ImportLog Model
| Field | Type | Required | Indexed | Description |
|-------|------|----------|---------|-------------|
| id | Integer | Yes (PK) | Yes | Primary key |
| batch_id | String(100) | Yes | Yes (Unique) | Unique batch ID |
| import_type | String(50) | Yes | Yes | excel, csv, api, etc. |
| status | String(50) | Yes | Yes | running, completed, etc. |
| items_processed | Integer | Yes | No | Total items processed |

## Status Values

### Slab.status
- `available` - Ready for sale
- `reserved` - Held for customer
- `sold` - Sold and invoiced
- `damaged` - Not sellable
- `archived` - Historical

### Shipment.status
- `pending` - Order placed
- `in_transit` - Currently shipping
- `received` - Delivered
- `cancelled` - Cancelled
- `delayed` - Date changed

### ImportLog.status
- `running` - In progress
- `completed` - Finished successfully
- `failed` - Import failed
- `partial` - Some items failed

## Database Configuration

Default SQLite database: `sqlite:///./data/slabhub.db`

Change via environment variable:
```bash
DATABASE_URL=postgresql://user:pass@localhost/slabhub
```

## Troubleshooting

**Database locked error:**
```python
# Sessions must be closed
db = SessionLocal()
try:
    # operations
    db.commit()
finally:
    db.close()
```

**Table doesn't exist:**
```python
from backend.app.models import init_db
init_db()
```

**Import error:**
```bash
pip install sqlalchemy pydantic-settings
```

## File Locations

- Models: `backend/app/models/`
- Config: `backend/app/config.py`
- Database: `./data/slabhub.db` (default)
- Test: `test_models.py`

## Test Database

```bash
# Run test script
python test_models.py

# Or test manually
python -c "from backend.app.models import init_db; init_db(); print('Database initialized!')"
```

---

**Quick Start:**
1. `from backend.app.models import init_db; init_db()`
2. `from backend.app.models import Slab, SessionLocal`
3. Create, query, update models using SessionLocal()
4. Always close sessions: `db.close()`
