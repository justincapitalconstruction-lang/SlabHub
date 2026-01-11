# Technical Specification: SlabHub Inventory System

## Task Complexity Assessment
**Level: HARD**

Rationale:
- Full-stack application with FastAPI backend and web frontend
- Complex data model with multiple entity types (Slabs, InventoryItems, Shipments)
- Multiple integration points (SlabCrop via filesystem, existing metadata files)
- File watching and async processing requirements
- Image processing with perceptual hashing for duplicate detection
- QR code generation and PDF label printing
- Windows-specific deployment with LAN accessibility
- Data migration/import from multiple sources
- Must be production-ready by Monday with no critical TODOs

## Technical Context

### Language & Framework
- **Backend**: Python 3.9+ with FastAPI
- **Frontend**: Jinja2 templates, minimal JavaScript
- **Database**: SQLite (simple, file-based, suitable for Monday launch)
- **Server**: Uvicorn ASGI server

### Key Dependencies
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pydantic==2.5.0
pydantic-settings==2.1.0
python-multipart==0.0.6
jinja2==3.1.2
pillow==10.1.0
imagehash==4.3.1
qrcode[pil]==7.4.2
reportlab==4.0.7
watchdog==3.0.0
python-dotenv==1.0.0
```

### File System Structure
```
slabhub/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Settings/env var loader
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── models.py               # DB models
│   │   ├── schemas.py              # Pydantic schemas
│   │   ├── crud.py                 # Database operations
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── image_processing.py # Perceptual hash, validation
│   │   │   ├── qr_generator.py     # QR code generation
│   │   │   ├── label_printer.py    # PDF label generation
│   │   │   └── duplicate_detection.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── slabs.py            # Slab CRUD endpoints
│   │   │   ├── inventory.py        # InventoryItem endpoints
│   │   │   ├── shipments.py        # Shipment endpoints
│   │   │   ├── admin.py            # Admin UI routes
│   │   │   ├── kiosk.py            # Kiosk/public viewer
│   │   │   └── import_routes.py    # Import status/trigger
│   │   └── templates/
│   │       ├── base.html
│   │       ├── admin/
│   │       │   ├── slabs_list.html
│   │       │   ├── slab_detail.html
│   │       │   ├── inventory_list.html
│   │       │   ├── inventory_detail.html
│   │       │   ├── shipments_list.html
│   │       │   ├── shipment_detail.html
│   │       │   └── import_status.html
│   │       └── kiosk/
│   │           ├── browse.html
│   │           └── slab_view.html
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       └── main.js
│   ├── .env.example
│   └── requirements.txt
├── scripts/
│   ├── watch_slabcrop_output.py    # Folder watcher service
│   ├── import_metadata.py          # One-time metadata import
│   └── import_folder.py            # Bulk folder import
├── data/
│   ├── incoming_raw/               # Drop raw photos here
│   ├── slabcrop_inbox/             # SlabCrop input (optional)
│   ├── slabcrop_outbox/            # SlabCrop output watch folder
│   ├── processed/                  # Archive for processed images
│   ├── logs/                       # Import and process logs
│   └── slabhub.db                  # SQLite database
├── .gitignore
├── README.md
└── runbook.md                      # Monday deployment guide
```

## Assumptions & Design Decisions

### Assumptions
1. **Missing Repository**: Task description references existing SlabHub project, but repo is empty. Building from scratch.
2. **External Config Files**: `sortly_builder_config.json` and `stone-identifications.json` exist on deployment machine but not in repo. Will read from configured paths.
3. **SlabCrop Integration**: SlabCrop.exe is a black box that processes images. We only monitor its output folder.
4. **Network Access**: Application runs on local Windows PC accessible via LAN (http://PC_IP:8000).
5. **Single Machine**: All components run on same Windows machine initially.
6. **PM-241BT Printer**: Accepts PDF files for printing; we generate 4x6 inch PDFs.
7. **No Authentication for Monday**: Multi-user support deferred; basic auth can be added later.

### Design Decisions
1. **Database**: SQLite for simplicity and portability; can migrate to PostgreSQL later if needed.
2. **File Watching**: Use `watchdog` library for cross-platform folder monitoring.
3. **Duplicate Detection**: Perceptual hashing (pHash) via `imagehash` library with configurable threshold.
4. **QR Code Format**: Encode `{PUBLIC_BASE_URL}/s/{public_id}` in QR codes.
5. **Label Layout**: 4x6 inch PDF with QR code (2x2 inch), slab name, dimensions, stone type.
6. **Image Validation**: Check readability, min dimensions (800x800), not all-black/white.
7. **Import Idempotency**: Use perceptual hash to prevent re-importing same images.
8. **Logging**: Structured logs with timestamps to `data/logs/import_YYYYMMDD_HHMMSS.log`.
9. **Configuration**: All paths and settings via environment variables with sensible defaults.
10. **Frontend**: Server-side rendered Jinja2 templates; minimal JS for progressive enhancement.

## Data Model

### Slabs Table
```sql
CREATE TABLE slabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    public_id TEXT UNIQUE NOT NULL,              -- Short alphanumeric ID for QR
    name TEXT NOT NULL,
    stone_type TEXT,                             -- Granite, Marble, Quartzite, etc.
    supplier TEXT,
    finish TEXT,                                 -- Polished, Honed, Leathered
    thickness REAL,                              -- inches
    length REAL,                                 -- inches
    width REAL,                                  -- inches
    location TEXT,                               -- Warehouse location
    status TEXT DEFAULT 'in_stock',              -- in_stock, sold, reserved, damaged
    tags TEXT,                                   -- JSON array of tags
    notes TEXT,
    image_path TEXT,                             -- Primary image path
    image_hash TEXT,                             -- Perceptual hash for deduplication
    qr_code_path TEXT,                           -- Generated QR code image
    extra_json TEXT,                             -- JSON blob for unmapped fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### InventoryItems Table
```sql
CREATE TABLE inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,                               -- hardware, tools, consumables
    unit TEXT DEFAULT 'each',                    -- each, box, pallet
    qty_on_hand REAL DEFAULT 0,
    location TEXT,
    tags TEXT,                                   -- JSON array
    notes TEXT,
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Shipments Table
```sql
CREATE TABLE shipments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_number TEXT UNIQUE NOT NULL,
    supplier TEXT,
    received_date DATE,
    status TEXT DEFAULT 'pending',               -- pending, received, partial
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### ShipmentItems Table
```sql
CREATE TABLE shipment_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shipment_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,                     -- 'slab' or 'inventory'
    item_id INTEGER NOT NULL,                    -- Foreign key to slabs or inventory_items
    quantity REAL NOT NULL,
    received_quantity REAL DEFAULT 0,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id)
);
```

### ImportLog Table
```sql
CREATE TABLE import_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_type TEXT NOT NULL,                   -- 'metadata', 'folder', 'slabcrop'
    source_path TEXT,
    status TEXT,                                 -- 'success', 'partial', 'failed'
    items_processed INTEGER DEFAULT 0,
    items_created INTEGER DEFAULT 0,
    items_updated INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    error_details TEXT,                          -- JSON array of errors
    started_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

## API Endpoints

### Admin/CRUD Routes
- `GET /admin/` - Admin dashboard
- `GET /admin/slabs` - List slabs with filters/search
- `GET /admin/slabs/{id}` - Slab detail/edit form
- `POST /admin/slabs/{id}` - Update slab
- `DELETE /admin/slabs/{id}` - Delete slab
- `GET /admin/inventory` - List inventory items
- `GET /admin/inventory/{id}` - Inventory detail/edit
- `POST /admin/inventory/{id}` - Update inventory
- `GET /admin/shipments` - List shipments
- `GET /admin/shipments/{id}` - Shipment detail/receive form
- `POST /admin/shipments/{id}/receive` - Process receiving

### Import Routes
- `GET /admin/import-status` - View import history
- `POST /admin/import/metadata` - Trigger metadata import
- `POST /admin/import/folder` - Trigger folder import
- `GET /admin/import/watcher-status` - Check watcher service status

### Public/Kiosk Routes
- `GET /` - Redirect to kiosk
- `GET /kiosk` - Kiosk browse view with search
- `GET /s/{public_id}` - Public slab view (QR target)
- `GET /api/search` - JSON search endpoint for AJAX

### Label/QR Generation
- `GET /admin/labels/slab/{id}` - Generate single slab label PDF
- `POST /admin/labels/batch` - Generate batch labels (returns multi-page PDF or ZIP)

## Implementation Approach

### Phase 1: Foundation (Priority 1 - Monday Critical)
1. **Project scaffolding**
   - Initialize FastAPI app with proper structure
   - Set up SQLAlchemy models and database initialization
   - Configure environment variables and settings loader
   - Create .gitignore (exclude .env, data/, *.db, __pycache__)

2. **Core data models**
   - Implement all SQLAlchemy models
   - Create database initialization script
   - Add CRUD operations in crud.py

3. **Basic admin interface**
   - Slabs list/detail/edit views
   - Basic search functionality
   - Form handling for create/update

### Phase 2: Import & Integration (Priority 1 - Monday Critical)
4. **Perceptual hashing & duplicate detection**
   - Implement image hash calculation (pHash)
   - Duplicate detection logic with configurable threshold
   - Image validation (dimensions, readability, not blank)

5. **Metadata importer**
   - Read and parse stone-identifications.json
   - Map fields to Slab model
   - Handle missing/extra fields gracefully
   - Log import results

6. **SlabCrop watcher service**
   - Monitor SLABCROP_OUTPUT_FOLDER using watchdog
   - Validate new images
   - Check for duplicates
   - Create/update slab records
   - Move processed images to archive
   - Log all operations

### Phase 3: Labels & QR (Priority 1 - Monday Critical)
7. **QR code generation**
   - Generate QR codes encoding public slab URLs
   - Store QR images in data/qr/ or embed in database

8. **PDF label generation**
   - ReportLab-based 4x6 inch label layout
   - Include QR code, slab name, dimensions, stone type
   - Support batch generation

### Phase 4: Search & Kiosk (Priority 1 - Monday Critical)
9. **Enhanced search**
   - Fast text search across name, stone_type, supplier, location
   - Filter by status, tags
   - Return JSON for AJAX or render template

10. **Kiosk interface**
    - Large tile cards for browsing
    - Quick filters
    - Mobile-responsive for tablet kiosks

11. **Public slab view**
    - Clean, simple view for QR code targets
    - Display slab details and primary image
    - Fast loading

### Phase 5: Inventory & Receiving (Priority 2 - Can be minimal for Monday)
12. **InventoryItems CRUD**
    - Basic list/detail/edit views
    - Search functionality

13. **Shipments & Receiving**
    - Create shipment
    - Add items to shipment
    - Receive items (update quantities)

### Phase 6: Documentation & Deployment (Priority 1 - Monday Critical)
14. **Documentation**
    - README.md with setup instructions
    - runbook.md with Monday deployment checklist
    - How to configure .env
    - How to run watcher service
    - How to import existing library
    - Printer setup guide

15. **Deployment preparation**
    - Create .env.example with all variables
    - requirements.txt
    - Database initialization script
    - Systemd/Windows service config for watcher (optional)

## Configuration (Environment Variables)

```bash
# Database
DATABASE_URL=sqlite:///./data/slabhub.db

# Application
PUBLIC_BASE_URL=http://192.168.1.100:8000
HOST=0.0.0.0
PORT=8000
DEBUG=false

# SlabCrop Integration
SLABCROP_OUTPUT_FOLDER=D:/SlabCrop/output
SLABCROP_INBOX_FOLDER=./data/slabcrop_inbox
INCOMING_RAW_FOLDER=./data/incoming_raw
PROCESSED_ARCHIVE_FOLDER=./data/processed

# Import Paths
IMPORT_METADATA_FILE=D:/CSSPS/kiosk-frontend/stone-identifications.json
IMPORT_INPUT_FOLDER=D:/sortly_automated_upload/images confirmed/images_final

# Image Processing
IMAGE_MIN_WIDTH=800
IMAGE_MIN_HEIGHT=800
DUPLICATE_THRESHOLD=10

# Label Generation
LABEL_SIZE=4x6
LABEL_OUTPUT_FOLDER=./data/labels

# Logging
LOG_FOLDER=./data/logs
LOG_ROTATION_DAYS=30
```

## Verification Approach

### Manual Testing Checklist
1. **Database initialization**
   - Run app, verify tables created
   - Insert test slab, verify fields

2. **Admin interface**
   - Create/edit/delete slab
   - Search functionality works
   - Forms validate properly

3. **Import functionality**
   - Run metadata import, check logs
   - Verify slabs created correctly
   - Check duplicate detection works

4. **SlabCrop watcher**
   - Drop test image in output folder
   - Verify watcher detects it
   - Check validation logic
   - Confirm image archived
   - Check slab created in DB

5. **QR & Labels**
   - Generate QR code for test slab
   - Scan QR with phone on LAN
   - Verify correct page loads
   - Generate PDF label
   - Verify layout looks correct at 4x6

6. **Kiosk**
   - Browse slabs
   - Search by name/type
   - Filter by status
   - View slab detail

7. **Public view**
   - Access /s/{public_id}
   - Verify fast load
   - Check mobile responsive

### Automated Testing
- Unit tests for duplicate detection logic
- Unit tests for image validation
- Integration tests for import functions
- API endpoint tests with pytest

### Performance Testing
- Search response time < 500ms for 1000+ slabs
- Public view loads in < 1s
- Watcher processes image within 5s of detection

### Deployment Verification
1. Copy to Windows PC
2. Create virtual environment
3. Install dependencies
4. Configure .env with correct paths
5. Initialize database
6. Start FastAPI server
7. Start watcher service
8. Access from another device on LAN
9. Import existing library
10. Generate and print test label

## Risk Mitigation

### High-Risk Areas
1. **SlabCrop integration** - Black box, unknown output format
   - Mitigation: Robust validation, detailed logging, manual review queue
   
2. **Duplicate detection accuracy** - False positives/negatives
   - Mitigation: Configurable threshold, manual review interface, ability to link/unlink duplicates
   
3. **Windows file paths** - Hardcoded D: drive paths
   - Mitigation: All paths via .env, sensible relative path defaults, path validation on startup
   
4. **Network accessibility** - LAN access issues
   - Mitigation: Document firewall configuration, test with multiple devices, provide troubleshooting guide
   
5. **Printer compatibility** - PM-241BT PDF rendering
   - Mitigation: Test label layout early, provide alternative sizes, include sample PDFs in docs

### Blockers
- If stone-identifications.json format is incompatible, create manual mapping interface
- If SlabCrop output varies, implement flexible parser with config options
- If PM-241BT doesn't handle PDF well, provide PNG/JPG label export option

## Success Criteria

### Must-Have for Monday
- ✅ Import existing slab library from metadata file
- ✅ SlabCrop watcher running and processing new images
- ✅ Admin interface for browsing and editing slabs
- ✅ Fast search across all slab fields
- ✅ QR code generation with correct public URLs
- ✅ PDF label generation compatible with PM-241BT
- ✅ Kiosk interface accessible on LAN
- ✅ Public slab view works from QR scans
- ✅ Duplicate detection prevents re-imports
- ✅ Comprehensive runbook for deployment

### Nice-to-Have (can defer)
- Inventory items full CRUD
- Shipment receiving workflow
- Batch label printing (multi-page PDF)
- Image gallery for slabs with multiple photos
- Advanced filters (by dimension range, etc.)
- Export functionality (CSV, Excel)
- User authentication

## Dependencies Between Components

```
Database Models
    ↓
CRUD Operations
    ↓
├─→ Admin Routes → Templates
├─→ Kiosk Routes → Templates  
├─→ Import Scripts
└─→ Watcher Service

Image Processing Utils
    ↓
├─→ Import Scripts
└─→ Watcher Service

QR/Label Utils
    ↓
└─→ Admin Routes
```

## Timeline Estimate
- Phase 1 (Foundation): 2-3 hours
- Phase 2 (Import): 3-4 hours
- Phase 3 (Labels/QR): 2 hours
- Phase 4 (Search/Kiosk): 2-3 hours
- Phase 5 (Inventory): 1-2 hours (minimal)
- Phase 6 (Docs): 1 hour
- Testing & Fixes: 2-3 hours
- **Total: 13-18 hours**

Given Monday deadline, focus on Phases 1-4 and 6. Phase 5 can be scaffolded minimally.
