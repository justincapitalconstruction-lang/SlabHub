# SlabHub Inventory System - Implementation Plan

## Configuration
- **Artifacts Path**: .zenflow/tasks/new-task-4426
- **Complexity**: HARD
- **Deadline**: Monday (production ready)

---

## Workflow Steps

### [x] Step: Technical Specification

Created comprehensive technical specification in `spec.md` covering:
- Full system architecture for SlabHub inventory system
- Data models for Slabs, InventoryItems, Shipments
- API endpoints and routing structure
- File system layout and integration points
- Configuration via environment variables
- Risk mitigation strategies
- Success criteria for Monday launch

---

### [ ] Step 1: Project Foundation & Database

**Objective**: Set up project structure, dependencies, and database layer

**Tasks**:
- Create FastAPI project structure (backend/app/, scripts/, data/)
- Initialize requirements.txt with all dependencies
- Create .env.example with all configuration variables
- Set up .gitignore (exclude .env, data/, *.db, __pycache__, logs/)
- Implement config.py with Pydantic Settings for env var loading
- Implement database.py with SQLAlchemy engine and session management
- Create models.py with Slabs, InventoryItems, Shipments, ShipmentItems, ImportLog models
- Create schemas.py with Pydantic models for request/response validation
- Implement database initialization script (create tables)

**Verification**:
- Run initialization script successfully
- Verify all tables created in SQLite database
- Confirm .env loads correctly with defaults

**Files Created/Modified**:
- `requirements.txt`
- `.env.example`
- `.gitignore`
- `backend/app/__init__.py`
- `backend/app/config.py`
- `backend/app/database.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `scripts/init_db.py`

---

### [ ] Step 2: Image Processing & Duplicate Detection

**Objective**: Implement image validation and perceptual hashing for duplicate detection

**Tasks**:
- Create utils/image_processing.py module
- Implement image validation (readability, dimensions, not blank)
- Implement perceptual hash calculation using imagehash (pHash algorithm)
- Create utils/duplicate_detection.py module
- Implement duplicate detection logic with configurable threshold
- Add hash comparison function (Hamming distance)
- Write unit tests for validation and hashing functions

**Verification**:
- Test with various image formats (JPEG, PNG)
- Verify blank images detected
- Verify duplicate detection with similar images
- Confirm false positive rate is acceptable

**Files Created/Modified**:
- `backend/app/utils/__init__.py`
- `backend/app/utils/image_processing.py`
- `backend/app/utils/duplicate_detection.py`
- `tests/test_image_processing.py` (optional)

---

### [ ] Step 3: CRUD Operations & Basic Admin

**Objective**: Implement database CRUD operations and basic admin interface

**Tasks**:
- Create crud.py with functions for all models (create, read, update, delete)
- Implement search/filter functions for slabs (by name, type, supplier, status)
- Create routers/slabs.py with API endpoints
- Create routers/admin.py with admin HTML routes
- Set up Jinja2 templates directory and base.html template
- Create templates/admin/slabs_list.html with search form
- Create templates/admin/slab_detail.html with edit form
- Create static/css/styles.css with basic styling
- Implement main.py with FastAPI app setup and router registration

**Verification**:
- Start server and access /admin/slabs
- Create test slab via form
- Edit slab details
- Search for slab by name
- Delete test slab

**Files Created/Modified**:
- `backend/app/crud.py`
- `backend/app/routers/__init__.py`
- `backend/app/routers/slabs.py`
- `backend/app/routers/admin.py`
- `backend/app/main.py`
- `backend/app/templates/base.html`
- `backend/app/templates/admin/slabs_list.html`
- `backend/app/templates/admin/slab_detail.html`
- `backend/static/css/styles.css`

---

### [ ] Step 4: Metadata Import from stone-identifications.json

**Objective**: Import existing slab library from metadata file

**Tasks**:
- Create scripts/import_metadata.py
- Implement JSON file reader and validator
- Map JSON fields to Slab model (handle name, stone_type, supplier, dimensions, etc.)
- Store unmapped fields in extra_json column
- Calculate perceptual hash for each image during import
- Check for duplicates before creating records
- Generate detailed import log (items processed, created, skipped, failed)
- Save import results to ImportLog table
- Create admin route to trigger import: POST /admin/import/metadata
- Add import status template to display results

**Verification**:
- Run import script with sample data
- Verify slabs created correctly in database
- Check that duplicate images are detected and skipped
- Confirm unmapped fields preserved in extra_json
- Review import log for completeness

**Files Created/Modified**:
- `scripts/import_metadata.py`
- `backend/app/routers/import_routes.py`
- `backend/app/templates/admin/import_status.html`

---

### [ ] Step 5: SlabCrop Watcher Service

**Objective**: Monitor SlabCrop output folder and auto-import new images

**Tasks**:
- Create scripts/watch_slabcrop_output.py using watchdog library
- Implement FileSystemEventHandler for image file events
- On new file detected:
  - Wait for file write completion (avoid partial reads)
  - Validate image (dimensions, readability, not blank)
  - Calculate perceptual hash
  - Check for duplicates in database
  - If not duplicate, create new Slab record
  - Move processed image to archive folder
  - Log all operations
- Implement graceful shutdown handling
- Add command-line arguments for config override
- Create logging with rotation to data/logs/
- Add watcher status endpoint: GET /admin/import/watcher-status

**Verification**:
- Start watcher service manually
- Drop test image in SLABCROP_OUTPUT_FOLDER
- Verify image detected within 5 seconds
- Confirm slab created in database
- Check image moved to archive
- Review log file for detailed trace
- Test with duplicate image (should skip)
- Test with invalid image (should log error)

**Files Created/Modified**:
- `scripts/watch_slabcrop_output.py`
- `backend/app/routers/import_routes.py` (update with watcher status)

---

### [ ] Step 6: QR Code Generation

**Objective**: Generate QR codes for slab identification

**Tasks**:
- Create utils/qr_generator.py module
- Implement QR code generation using qrcode library
- QR encodes: {PUBLIC_BASE_URL}/s/{public_id}
- Generate short alphanumeric public_id (8 chars, base62)
- Save QR image to data/qr/{public_id}.png
- Update Slab model to include qr_code_path field (if not already)
- Add QR generation function to CRUD operations
- Auto-generate QR on slab creation
- Add endpoint to regenerate QR: POST /admin/slabs/{id}/generate-qr

**Verification**:
- Create test slab, verify QR generated
- Scan QR with phone on LAN
- Confirm correct URL encoded
- Verify QR image saved to disk

**Files Created/Modified**:
- `backend/app/utils/qr_generator.py`
- `backend/app/crud.py` (update with QR generation)
- `backend/app/routers/slabs.py` (add regenerate endpoint)

---

### [ ] Step 7: PDF Label Generation

**Objective**: Generate PDF labels for PM-241BT printer

**Tasks**:
- Create utils/label_printer.py module
- Implement 4x6 inch PDF layout using ReportLab
- Layout includes:
  - QR code (2x2 inches, top-left)
  - Slab name (large, bold)
  - Stone type, finish, supplier
  - Dimensions (L x W x Thickness)
- Support configurable LABEL_SIZE from .env
- Add endpoint: GET /admin/labels/slab/{id} - returns PDF
- Add batch label generation: POST /admin/labels/batch (accepts slab IDs)
- Return ZIP of PDFs or multi-page PDF for batch

**Verification**:
- Generate label for test slab
- Open PDF, verify layout correct at 4x6 inches
- Test print on PM-241BT printer or regular printer
- Verify QR code scannable from printed label
- Generate batch of 3 labels, verify all included

**Files Created/Modified**:
- `backend/app/utils/label_printer.py`
- `backend/app/routers/admin.py` (add label routes)

---

### [ ] Step 8: Public Slab View & Kiosk Interface

**Objective**: Create public-facing views for QR scan targets and browsing

**Tasks**:
- Create routers/kiosk.py with public routes
- Implement GET /s/{public_id} - public slab detail view
- Create templates/kiosk/slab_view.html - clean, mobile-responsive
- Implement GET /kiosk - browse interface with search
- Create templates/kiosk/browse.html - large tile cards
- Add search API endpoint: GET /api/search (JSON response)
- Implement fast text search across name, stone_type, supplier, location, tags
- Add filters: status, stone_type
- Add minimal JavaScript for AJAX search (optional, can be server-rendered)
- Ensure mobile responsiveness

**Verification**:
- Access /s/{public_id} from phone via QR scan
- Verify page loads in < 1 second
- Check mobile layout looks good
- Access /kiosk from tablet
- Test search by name, type
- Test filters
- Verify tile cards display correctly

**Files Created/Modified**:
- `backend/app/routers/kiosk.py`
- `backend/app/templates/kiosk/slab_view.html`
- `backend/app/templates/kiosk/browse.html`
- `backend/static/js/main.js` (optional)

---

### [ ] Step 9: Inventory Items & Shipments (Minimal)

**Objective**: Scaffold basic inventory and shipment management

**Tasks**:
- Create routers/inventory.py with CRUD endpoints
- Create templates/admin/inventory_list.html
- Create templates/admin/inventory_detail.html
- Add CRUD operations for InventoryItems in crud.py
- Create routers/shipments.py with basic endpoints
- Create templates/admin/shipments_list.html
- Create templates/admin/shipment_detail.html
- Implement simple receiving form (increment qty_on_hand)
- Add CRUD operations for Shipments and ShipmentItems in crud.py

**Note**: This is minimal scaffolding for Monday. Full receiving workflow can be enhanced post-launch.

**Verification**:
- Create test inventory item
- Create test shipment
- Add items to shipment
- Receive shipment items
- Verify quantities updated

**Files Created/Modified**:
- `backend/app/routers/inventory.py`
- `backend/app/routers/shipments.py`
- `backend/app/templates/admin/inventory_list.html`
- `backend/app/templates/admin/inventory_detail.html`
- `backend/app/templates/admin/shipments_list.html`
- `backend/app/templates/admin/shipment_detail.html`
- `backend/app/crud.py` (update)

---

### [ ] Step 10: Documentation & Deployment

**Objective**: Create comprehensive documentation for Monday deployment

**Tasks**:
- Create README.md with:
  - Project overview
  - Technology stack
  - Installation instructions (venv, pip install)
  - Configuration (.env setup)
  - Running the application
  - Running watcher service
- Create runbook.md with:
  - Pre-deployment checklist
  - Environment variable configuration guide
  - Database initialization steps
  - Starting services (FastAPI, watcher)
  - Network configuration (firewall, LAN access)
  - Testing checklist
  - Troubleshooting common issues
  - How to import existing library
  - Printer setup (PM-241BT PDF printing)
  - Backup and recovery procedures
- Add inline code comments where necessary (minimal, only for complex logic)
- Create sample .env.example with all variables documented

**Verification**:
- Follow README from scratch on clean machine
- Follow runbook step-by-step
- Verify all instructions are accurate and complete

**Files Created/Modified**:
- `README.md`
- `runbook.md`
- `.env.example` (update with comments)

---

### [ ] Step 11: Integration Testing & Bug Fixes

**Objective**: End-to-end testing and fix critical issues

**Tasks**:
- Test complete workflow:
  1. Initialize database
  2. Import metadata from stone-identifications.json
  3. Start watcher service
  4. Drop test image in SlabCrop output folder
  5. Verify slab created
  6. Generate QR and label
  7. Access from phone via QR
  8. Test kiosk search
- Test on Windows PC (target deployment platform)
- Fix path separator issues (Windows backslashes)
- Test LAN accessibility from multiple devices
- Verify all file paths work with configured drives
- Load test search with 100+ slabs
- Fix any critical bugs found
- Optimize slow queries if needed

**Verification**:
- Complete end-to-end test passes
- No critical errors in logs
- Search responds in < 500ms
- QR scan works reliably
- Labels print correctly

**Files Modified**:
- Various bug fixes across codebase

---

## Post-Monday Enhancements (Deferred)

The following features can be added after Monday launch:
- User authentication and role-based access control
- Advanced search filters (dimension ranges, date ranges)
- Image gallery for slabs with multiple photos
- Bulk edit operations
- CSV/Excel export functionality
- Reporting and analytics
- Email notifications for low inventory
- Integration with accounting systems
- Mobile app for warehouse workers
- Barcode scanning (in addition to QR)

---

## Risk Register

| Risk | Impact | Mitigation | Status |
|------|--------|------------|--------|
| stone-identifications.json format incompatible | High | Flexible parser, manual mapping interface | Monitor |
| SlabCrop output varies | Medium | Robust validation, configurable parsing | Monitor |
| PM-241BT printer doesn't handle PDF | High | Test early, provide PNG export fallback | Monitor |
| LAN access blocked by firewall | High | Document firewall config, test early | Monitor |
| Duplicate detection false positives | Medium | Configurable threshold, manual review UI | Monitor |
| Database performance with 1000+ slabs | Low | Add indexes, pagination | Monitor |

---

## Success Metrics

- [ ] Import existing slab library (100+ items)
- [ ] SlabCrop watcher processes images within 5 seconds
- [ ] Search returns results in < 500ms
- [ ] QR codes scannable and load correct page
- [ ] Labels print correctly on PM-241BT
- [ ] No critical bugs in 1 hour of testing
- [ ] Complete documentation for deployment
- [ ] Successful deployment on Windows PC with LAN access
