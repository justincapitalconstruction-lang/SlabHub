# Database Migration Guide

## Current Schema Version

**Initial Schema Version 1.0** - Created 2026-01-10

This document provides guidance for managing database schema changes in the SlabHub inventory system.

## SQLite Development Considerations

### Limitations

SQLite has limited `ALTER TABLE` support:
- ✅ Can add new columns
- ❌ Cannot modify existing columns
- ❌ Cannot delete columns (requires table recreation)
- ❌ Cannot change column types (requires table recreation)

### Recommended Approach

For development with SQLite:
1. **Minor changes** - Use ALTER TABLE to add columns
2. **Major changes** - Recreate the database
3. **Production** - Use Alembic for migrations

## Adding New Columns (SQLite Safe)

### 1. Update the Model

Edit the relevant model file (e.g., `slab.py`):

```python
# Add new field to Slab model
barcode: Mapped[str | None] = mapped_column(
    String(100),
    nullable=True,
    index=True,
    comment="Barcode number"
)
```

### 2. Generate Migration SQL

SQLite-compatible migration:

```sql
ALTER TABLE slabs ADD COLUMN barcode VARCHAR(100);
CREATE INDEX idx_slab_barcode ON slabs(barcode);
```

### 3. Apply Migration

```python
from backend.app.models.base import engine

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE slabs ADD COLUMN barcode VARCHAR(100)"))
    conn.execute(text("CREATE INDEX idx_slab_barcode ON slabs(barcode)"))
    conn.commit()
```

## Modifying Columns (Requires Recreation)

### 1. Export Existing Data

```python
from backend.app.models import Slab, SessionLocal
import json

db = SessionLocal()
slabs = db.query(Slab).all()

# Export to JSON
with open('slabs_backup.json', 'w') as f:
    json.dump([slab.to_dict() for slab in slabs], f, default=str)

db.close()
```

### 2. Drop and Recreate Tables

```python
from backend.app.models.base import Base, engine

# Drop all tables
Base.metadata.drop_all(bind=engine)

# Modify models in code
# ... make your changes ...

# Recreate all tables
Base.metadata.create_all(bind=engine)
```

### 3. Reimport Data

```python
from backend.app.models import Slab, SessionLocal
import json

with open('slabs_backup.json', 'r') as f:
    slabs_data = json.load(f)

db = SessionLocal()
for data in slabs_data:
    # Remove fields that don't exist in new schema
    data.pop('id', None)  # Let DB generate new IDs

    # Create new record
    slab = Slab(**data)
    db.add(slab)

db.commit()
db.close()
```

## Using Alembic (Production Recommended)

### 1. Install Alembic

```bash
pip install alembic
```

### 2. Initialize Alembic

```bash
cd backend
alembic init alembic
```

### 3. Configure Alembic

Edit `alembic/env.py`:

```python
from backend.app.models.base import Base
from backend.app.config import settings

# Set target metadata
target_metadata = Base.metadata

# Set database URL
config.set_main_option("sqlalchemy.url", settings.database_url)
```

Edit `alembic.ini`:

```ini
# Replace this line:
# sqlalchemy.url = driver://user:pass@localhost/dbname

# With:
sqlalchemy.url = sqlite:///./data/slabhub.db
```

### 4. Create Initial Migration

```bash
alembic revision --autogenerate -m "Initial schema"
```

### 5. Review Migration

Check `alembic/versions/xxxx_initial_schema.py`:

```python
def upgrade():
    # Auto-generated upgrade commands
    op.create_table('slabs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('public_id', sa.String(50), nullable=False),
        # ... more columns
    )

def downgrade():
    # Auto-generated downgrade commands
    op.drop_table('slabs')
```

### 6. Apply Migration

```bash
alembic upgrade head
```

### 7. Create New Migration

When you modify models:

```bash
# 1. Edit model files
# 2. Generate migration
alembic revision --autogenerate -m "Add barcode field to slabs"

# 3. Review generated migration
# 4. Apply migration
alembic upgrade head
```

## Migration Best Practices

### 1. Always Backup Data

Before any schema change:

```python
from backend.app.models import SessionLocal, Slab
import json
from datetime import datetime

db = SessionLocal()

# Backup all tables
backup = {
    'timestamp': datetime.now().isoformat(),
    'slabs': [s.to_dict() for s in db.query(Slab).all()],
    # ... other tables
}

with open(f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
    json.dump(backup, f, default=str, indent=2)

db.close()
```

### 2. Test Migrations

Always test on a copy of production data:

```bash
# Copy production database
cp data/slabhub.db data/slabhub_test.db

# Set test database
export DATABASE_URL=sqlite:///./data/slabhub_test.db

# Run migration
alembic upgrade head

# Test the application
python -m pytest

# If successful, apply to production
```

### 3. Version Control Migrations

```bash
# Add migration files to git
git add alembic/versions/
git commit -m "Add migration: Add barcode field to slabs"
```

### 4. Document Schema Changes

Update this file with each schema change:

```markdown
## Schema History

### Version 1.1 - 2026-01-15
- Added `barcode` field to Slab model
- Added index on `barcode`

### Version 1.2 - 2026-02-01
- Added `vendor_id` field to Slab model
- Created `vendors` table
- Added foreign key relationship
```

## Common Migration Scenarios

### Adding a Required Field

```python
# 1. Add as nullable first
barcode: Mapped[str | None] = mapped_column(String(100), nullable=True)

# 2. Populate existing records
db = SessionLocal()
slabs = db.query(Slab).filter(Slab.barcode.is_(None)).all()
for slab in slabs:
    slab.barcode = f"BC-{slab.id:08d}"
db.commit()
db.close()

# 3. Make non-nullable in next migration
barcode: Mapped[str] = mapped_column(String(100), nullable=False)
```

### Adding an Index

```python
# In migration file:
def upgrade():
    op.create_index('idx_slab_barcode', 'slabs', ['barcode'])

def downgrade():
    op.drop_index('idx_slab_barcode', 'slabs')
```

### Renaming a Column

```python
# SQLite doesn't support RENAME COLUMN directly
# Must recreate table

def upgrade():
    # Create new table with new column name
    op.rename_table('slabs', 'slabs_old')
    op.create_table('slabs', ...)

    # Copy data
    op.execute("""
        INSERT INTO slabs (id, public_id, ...)
        SELECT id, public_id, ... FROM slabs_old
    """)

    # Drop old table
    op.drop_table('slabs_old')

def downgrade():
    # Reverse process
    ...
```

### Adding a Foreign Key

```python
# 1. Create the referenced table first
class Vendor(Base):
    __tablename__ = "vendors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

# 2. Add foreign key to Slab
from sqlalchemy import ForeignKey

vendor_id: Mapped[int | None] = mapped_column(
    Integer,
    ForeignKey('vendors.id'),
    nullable=True,
    index=True
)

# 3. Create relationship
from sqlalchemy.orm import relationship

vendor: Mapped["Vendor"] = relationship("Vendor")
```

## Rollback Procedures

### Alembic Rollback

```bash
# Show current version
alembic current

# Rollback one version
alembic downgrade -1

# Rollback to specific version
alembic downgrade abc123

# Rollback all migrations
alembic downgrade base
```

### Manual Rollback (SQLite)

```bash
# 1. Stop application
# 2. Restore from backup
cp backups/slabhub_20260110.db data/slabhub.db

# 3. Restart application
```

## PostgreSQL Migration (Production)

### 1. Update Database URL

```bash
export DATABASE_URL=postgresql://user:password@localhost/slabhub
```

### 2. PostgreSQL-Specific Features

PostgreSQL supports more migration operations:

```python
# Change column type
op.alter_column('slabs', 'price',
    type_=sa.Numeric(precision=10, scale=2),
    existing_type=sa.Float()
)

# Add constraint
op.create_check_constraint(
    'price_positive',
    'slabs',
    'price > 0'
)

# Add partial index
op.execute("""
    CREATE INDEX idx_available_slabs
    ON slabs(location)
    WHERE status = 'available'
""")
```

### 3. Online Migrations

For zero-downtime deployments:

```python
# Add column as nullable first (doesn't lock table)
op.add_column('slabs', sa.Column('barcode', sa.String(100), nullable=True))

# Populate data in batches
op.execute("""
    UPDATE slabs
    SET barcode = 'BC-' || LPAD(id::text, 8, '0')
    WHERE barcode IS NULL
""")

# Add NOT NULL constraint (after data populated)
op.alter_column('slabs', 'barcode', nullable=False)
```

## Emergency Procedures

### Database Corruption

```bash
# 1. Stop application immediately
# 2. Copy corrupted database for analysis
cp data/slabhub.db data/slabhub_corrupted.db

# 3. Restore from latest backup
cp backups/slabhub_latest.db data/slabhub.db

# 4. Check integrity
sqlite3 data/slabhub.db "PRAGMA integrity_check"

# 5. Restart application
```

### Migration Failed Halfway

```bash
# Alembic tracks version in alembic_version table
# If migration failed, manually fix:

# 1. Restore from backup
# 2. Fix migration script
# 3. Try again

# Or force version:
alembic stamp head  # Mark as current
```

## Schema History

### Version 1.0 - 2026-01-10 (Initial)

**Tables Created:**
- `slabs` - Stone slab inventory (29 fields)
- `inventory_items` - General inventory (17 fields)
- `shipments` - Shipment tracking (13 fields)
- `import_logs` - Import operation logs (15 fields)

**Indexes Created:**
- 24 single-column indexes
- 6 composite indexes

**Features:**
- SQLAlchemy 2.0 syntax
- Automatic timestamps
- JSON fields for flexible data
- Foreign key enforcement
- Comprehensive indexing

---

**Next Schema Version:** TBD

For questions or issues, refer to SQLAlchemy documentation:
https://docs.sqlalchemy.org/en/20/
