# SlabHub Operations Runbook

This runbook provides day-to-day operational guidance for SlabHub. Use this as your primary reference for common tasks, maintenance procedures, and troubleshooting.

## Table of Contents
- [Daily Operations](#daily-operations)
- [Starting and Stopping Services](#starting-and-stopping-services)
- [Importing Existing Library](#importing-existing-library)
- [SlabCrop Integration](#slabcrop-integration)
- [Printer Operations](#printer-operations)
- [QR Code System](#qr-code-system)
- [Common Tasks](#common-tasks)
- [Monitoring and Logs](#monitoring-and-logs)
- [Database Operations](#database-operations)
- [Maintenance Procedures](#maintenance-procedures)
- [Common Issues and Fixes](#common-issues-and-fixes)

---

## Daily Operations

### Morning Startup Procedure

**Step 1: Start SlabHub Services**
```bash
# Navigate to SlabHub directory
cd C:\SlabHub

# Activate virtual environment
venv\Scripts\activate

# Start services
python scripts/start_services.py
```

**Step 2: Verify System Health**
```bash
# Check health endpoint
curl http://localhost:8000/health
```

Or open in browser: http://localhost:8000/health

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "database": "connected",
  "watch_folder_enabled": true,
  "watch_folder_running": true
}
```

**Step 3: Quick System Check**
- Open admin interface: http://localhost:8000/admin
- Open kiosk interface: http://localhost:8000/kiosk
- Check recent imports in admin
- Verify printer is online (if using labels)

### End of Day Shutdown Procedure

**Step 1: Review Logs**
```bash
# Check for any errors during the day
type data\logs\slabhub.log | findstr "ERROR"
```

**Step 2: Backup Database** (Recommended)
```bash
# Run daily backup
scripts\backup.bat

# Or manual backup:
copy data\slabhub.db data\backups\slabhub_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db
```

**Step 3: Stop Services**
```bash
# Press Ctrl+C in the terminal where SlabHub is running
# Or close the terminal window

# Verify services stopped:
curl http://localhost:8000/health
# Should fail to connect
```

**Optional: Leave Running**
- SlabHub can run 24/7 if needed
- Watch folder will continue monitoring SlabCrop
- Useful if SlabCrop processes images overnight

---

## Starting and Stopping Services

### Start Services

**Method 1: Using Start Script (Recommended)**
```bash
cd C:\SlabHub
venv\Scripts\activate
python scripts/start_services.py
```

This provides:
- Automatic service initialization
- Proper logging
- Graceful shutdown handling
- Watch folder activation

**Method 2: Direct Python Execution**
```bash
cd C:\SlabHub
venv\Scripts\activate
python backend/app/main.py
```

**Method 3: Uvicorn Direct**
```bash
cd C:\SlabHub
venv\Scripts\activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Stop Services

**Graceful Shutdown:**
- Press `Ctrl+C` in the terminal window
- Wait for "Shutdown Complete" message
- Services will cleanup properly

**Force Stop:**
```bash
# Find Python process
tasklist | findstr python

# Kill process
taskkill /IM python.exe /F
```

**Verify Stopped:**
```bash
# This should fail if stopped
curl http://localhost:8000/health
```

### Restart Services

```bash
# Stop (Ctrl+C)
# Then start again
python scripts/start_services.py
```

Or use the restart script:
```bash
# Create scripts\restart.bat:
@echo off
taskkill /IM python.exe /F
timeout /t 3
cd C:\SlabHub
call venv\Scripts\activate
python scripts\start_services.py
```

---

## Importing Existing Library

### Preparing Data for Import

**Step 1: Organize Your Data**

Create a JSON file with slab metadata. Supported formats:

**Option A: Array of Objects**
```json
[
  {
    "name": "Calacatta Gold",
    "stone_type": "Marble",
    "supplier": "Stone Supplier Co",
    "finish": "Polished",
    "thickness": 1.25,
    "length": 120,
    "width": 75,
    "location": "Warehouse A-1",
    "primary_image": "C:/images/calacatta_gold.jpg"
  },
  {
    "name": "Black Galaxy",
    "stone_type": "Granite",
    "supplier": "Stone Supplier Co",
    "finish": "Polished",
    "thickness": 1.25,
    "dimensions": "115x72",
    "location": "Warehouse B-3"
  }
]
```

**Option B: Single Object**
```json
{
  "name": "Carrara Marble",
  "type": "Marble",
  "vendor": "Italian Imports",
  "surface": "Honed",
  "thick": "3cm",
  "size": "120x75",
  "warehouse_location": "Zone C"
}
```

**Step 2: Field Mapping**

The importer automatically maps common field variations:

| Your Field | Maps To | Accepted Variations |
|------------|---------|---------------------|
| Name | `name` | name, title, description, slab_name, identifier |
| Type | `stone_type` | stone_type, type, material, stone, material_type |
| Vendor | `supplier` | supplier, vendor, source, provider |
| Surface | `finish` | finish, surface, surface_finish, treatment |
| Thickness | `thickness` | thickness, thick |
| Color | `color` | color, colour, primary_color |
| Size | `dimensions` | dimensions, size, dims |
| Length | `length` | length, len |
| Width | `width` | width, w |
| Area | `square_feet` | square_feet, sqft, sq_ft, area |
| Location | `location` | location, warehouse_location, storage_location |
| Image | `primary_image` | primary_image, image, image_path, photo, picture |

**Dimension Parsing:**
- "120x75" → length: 120, width: 75
- "120 x 75" → length: 120, width: 75
- "120 by 75" → length: 120, width: 75

### Running the Import

**Step 1: Preview Import (Dry Run)**
```bash
cd C:\SlabHub
venv\Scripts\activate

# Preview what will be imported
python scripts/import_metadata.py --file data/imports/your-data.json --dry-run
```

Review output:
- Number of items to be imported
- Any warnings or errors
- Field mappings
- Duplicate detection results

**Step 2: Run Actual Import**
```bash
# Import for real
python scripts/import_metadata.py --file data/imports/your-data.json
```

**Step 3: Verify Import**
```bash
# Run verification script
python scripts/verify_import.py
```

Or check admin interface:
- Open http://localhost:8000/admin
- View imported slabs
- Check import logs

### Import Options

**Custom File Location:**
```bash
python scripts/import_metadata.py --file C:/MyData/slabs.json
```

**Using Default Configuration:**
```bash
# Set in .env file:
IMPORT_METADATA_FILE=./data/imports/stone-identifications.json

# Then run without --file:
python scripts/import_metadata.py
```

### Import Troubleshooting

**Issue: "Missing required field 'name'"**
- Ensure each item has a name/title field
- Check JSON syntax is valid
- Verify field isn't empty or null

**Issue: "Failed to generate unique public_id"**
- Database may have collision issues
- Try running import again
- Check database isn't corrupted

**Issue: "Image file not found"**
- Verify image paths in JSON are absolute paths
- Check images exist at specified locations
- Ensure paths use forward slashes or escaped backslashes

**Issue: Duplicates Detected**
- Review duplicate warnings in output
- Use `--dry-run` to see what will be skipped
- Check perceptual hash threshold in `.env`

---

## SlabCrop Integration

### How SlabCrop Integration Works

**Workflow:**
1. SlabCrop processes raw slab images
2. SlabCrop saves processed images to output folder
3. SlabHub watch folder detects new images
4. SlabHub validates image (size, format, corruption)
5. SlabHub calculates perceptual hash
6. SlabHub checks for duplicates
7. SlabHub creates slab record in database
8. SlabHub generates QR code
9. SlabHub archives processed image
10. Slab is now available in kiosk and admin

**Key Components:**
- **Watch Folder**: Monitors SlabCrop output directory
- **Image Validator**: Ensures image quality
- **Perceptual Hash**: Prevents duplicate imports
- **Import Processor**: Handles image ingestion
- **Archive System**: Stores processed images

### Configure SlabCrop Output

**Step 1: Verify SlabCrop Output Folder**
1. Open SlabCrop application
2. Check Settings → Output Folder
3. Note the path (e.g., `D:\SlabCrop\output`)

**Step 2: Update SlabHub Configuration**

Edit `.env`:
```env
SLABCROP_OUTPUT_FOLDER=D:/SlabCrop/output
ENABLE_WATCH_FOLDER=true
```

Note: Use forward slashes `/` or escaped backslashes `\\` in paths.

**Step 3: Create Output Folder**
```bash
# If folder doesn't exist
mkdir D:\SlabCrop\output
```

**Step 4: Test Integration**
1. Process a test image through SlabCrop
2. Verify image appears in output folder
3. Check SlabHub logs for detection
4. Verify slab appears in admin interface

### Watch Folder Monitoring

**Check Watch Folder Status:**
```bash
# Via health endpoint
curl http://localhost:8000/health

# Look for:
# "watch_folder_enabled": true
# "watch_folder_running": true
```

**Monitor Watch Folder Activity:**
```bash
# Watch logs in real-time
Get-Content data\logs\slabhub.log -Wait | Select-String "watch"
```

**Manually Trigger Import:**

If watch folder isn't working, manually process images:
```bash
# Copy image to import folder
copy D:\SlabCrop\output\test_image.jpg data\incoming_raw\

# Process via import processor (future feature)
# Or add slab manually via admin interface
```

### Image Requirements

**Supported Formats:**
- PNG (.png)
- JPEG (.jpg, .jpeg)
- TIFF (.tiff, .tif)
- BMP (.bmp)

**Size Requirements:**
- Minimum width: 800px (configurable)
- Minimum height: 800px (configurable)
- Maximum file size: 10MB (configurable)

**Quality Checks:**
- Image must not be corrupted
- Image must open successfully
- Image dimensions must meet minimums

**Configure Requirements:**

Edit `.env`:
```env
IMAGE_MIN_WIDTH=800
IMAGE_MIN_HEIGHT=800
MAX_IMAGE_SIZE_MB=10
```

### Duplicate Detection

**How It Works:**
- Perceptual hash calculated for each image
- Hash compared against existing slabs
- Hamming distance determines similarity
- Threshold determines if duplicate (default: 10)

**Configure Threshold:**
```env
DUPLICATE_THRESHOLD=10
```

**Threshold Guide:**
- 0: Exact match only
- 5: Very similar (same image, minor edits)
- 10: Similar (recommended default)
- 15: Somewhat similar
- 20+: Loose matching (may have false positives)

**Override Duplicate Detection:**

Via admin interface:
- Mark slab as "duplicate ok"
- Import manually
- Adjust threshold temporarily

---

## Printer Operations

### PM-241BT Thermal Printer Setup

**Step 1: Install Printer Driver**
1. Download driver from manufacturer
2. Run installer
3. Connect printer via USB or Bluetooth
4. Complete driver installation
5. Print Windows test page

**Step 2: Configure Printer Settings**
1. Open "Printers & Scanners" in Windows
2. Find PM-241BT
3. Click "Manage" → "Printing preferences"
4. Set paper size: 4" x 6"
5. Set orientation: Portrait
6. Set quality: Best/600 DPI

**Step 3: Load Thermal Labels**
1. Open printer cover
2. Load 4x6" thermal label roll
3. Adjust guides to fit labels
4. Close cover
5. Run label alignment if needed

### Generating Labels

**Method 1: Via Admin Interface**
1. Open http://localhost:8000/admin
2. Find slab in list
3. Click "Generate Label"
4. PDF will download or print

**Method 2: Via API**
```bash
# Generate label PDF
curl -X POST http://localhost:8000/api/v1/slabs/{public_id}/label

# Example:
curl -X POST http://localhost:8000/api/v1/slabs/aB3x9Km2/label
```

**Method 3: Batch Label Generation**

Generate labels for multiple slabs:
```python
# In Python console
from backend.app.models import SessionLocal, Slab
from backend.app.utils.label_printer import generate_batch_labels
from pathlib import Path

db = SessionLocal()
slabs = db.query(Slab).filter(Slab.status == 'available').all()
pdf_path = generate_batch_labels(slabs, Path('data/labels'))
print(f"Batch labels: {pdf_path}")
db.close()
```

### Printing Labels

**Method 1: Print from PDF**
1. Open generated PDF from `data/labels/`
2. File → Print
3. Select PM-241BT printer
4. Print settings:
   - Paper size: 4x6"
   - Orientation: Portrait
   - Scale: Fit to page
5. Click Print

**Method 2: Direct Print from Application**
- Future feature: Direct printing from admin interface
- Currently: Generate PDF then print manually

**Method 3: Batch Print**
1. Open batch PDF (e.g., `labels_batch_20260110_120000.pdf`)
2. Print all pages at once
3. Each page is one label

### Label Layout

Standard SlabHub label (4x6 inches):

```
┌─────────────────────────────────┐
│ [QR]  CALACATTA GOLD           │
│ [QR]                           │
│ [QR]  Type: Marble             │
│       Finish: Polished         │
│       Supplier: Stone Co       │
│                                │
│       Dimensions: L:120" x W:75" x T:1.25"│
│       Area: 62.50 sq ft        │
│                                │
│       Location: Warehouse A-1  │
│                                │
│ ID: aB3x9Km2    2026-01-10 14:30│
└─────────────────────────────────┘
```

**Components:**
- QR Code: 2x2 inches (top-left)
- Slab Name: Large bold text
- Stone Type: Medium bold
- Details: Regular text
- Dimensions: Formatted
- Location: Bold (if available)
- Public ID: Bottom left (small)
- Timestamp: Bottom right (small)

### Printer Troubleshooting

**Labels Won't Print**
1. Check printer is online:
   ```bash
   # In PowerShell
   Get-Printer | Where-Object {$_.Name -like "*PM-241*"}
   ```
2. Verify USB/Bluetooth connection
3. Restart printer
4. Restart print spooler:
   ```bash
   net stop spooler
   net start spooler
   ```

**Labels Print Blank**
1. Check thermal paper isn't loaded backwards
2. Verify thermal ribbon (if not direct thermal)
3. Clean print head
4. Replace thermal paper roll

**Labels Print Cut Off**
1. Verify paper size: 4x6"
2. Check margins in PDF
3. Adjust label guides in printer
4. Regenerate label PDF

**Poor Print Quality**
1. Clean print head
2. Adjust darkness setting
3. Check thermal paper quality
4. Verify DPI setting: 203 or 300

---

## QR Code System

### How QR Codes Work

**QR Code URL Structure:**
```
http://192.168.1.100:8000/s/aB3x9Km2
                            │  │
                            │  └─ Slab public ID (8 characters)
                            └──── Short URL prefix
```

**Redirect Flow:**
1. User scans QR code with phone camera
2. Camera opens URL: `/s/aB3x9Km2`
3. SlabHub redirects to: `/kiosk/slab/aB3x9Km2`
4. User sees slab detail page with full info

### QR Code Generation

**Automatic Generation:**
- QR codes generated automatically when slab is created
- Stored in `data/qr/{public_id}.png`
- Embedded in labels

**Manual Regeneration:**
```python
# In Python console
from backend.app.utils.qr_generator import generate_qr_code

# Generate QR code for public ID
qr_path = generate_qr_code("aB3x9Km2")
print(f"QR code: {qr_path}")
```

**QR Code Settings:**
- Format: PNG
- Size: 500x500 pixels (configurable)
- Error correction: High (30% damage tolerance)
- Border: 4 modules (QR code quiet zone)

### Scanning QR Codes

**Compatible Devices:**
- iPhone (iOS 11+): Native camera app
- Android: Native camera app (most devices)
- QR code scanner apps

**Scanning Instructions:**
1. Open camera app on phone
2. Point at QR code on label
3. Wait for notification/popup
4. Tap notification to open URL
5. View slab details in kiosk

**Network Requirements:**
- Phone must be on same Wi-Fi network as SlabHub server
- Or server must be accessible via internet (if configured)

### Testing QR Codes

**Step 1: Generate Test QR Code**
```bash
# Via admin interface
# Or using Python:
python -c "from backend.app.utils.qr_generator import generate_qr_code; print(generate_qr_code('test123'))"
```

**Step 2: Test with QR Code Reader**
- Use phone camera
- Or online QR reader: https://webqr.com/
- Verify URL is correct

**Step 3: Test Full Flow**
1. Scan QR code with phone
2. Verify redirects to kiosk
3. Check slab details load correctly
4. Test on multiple devices

### QR Code Troubleshooting

**QR Code Doesn't Scan**
1. Ensure good lighting
2. Check QR code isn't damaged/blurred
3. Try different QR reader app
4. Regenerate QR code if corrupted

**QR Code Scans but Link Doesn't Work**
1. Verify `PUBLIC_BASE_URL` in `.env`:
   ```env
   PUBLIC_BASE_URL=http://192.168.1.100:8000
   ```
2. Check IP address is current:
   ```bash
   ipconfig
   ```
3. Test URL manually in phone browser
4. Verify firewall allows connections
5. Ensure phone on same network

**QR Code Shows Wrong Slab**
1. Check public_id in database
2. Verify QR code filename matches slab
3. Regenerate QR code
4. Clear browser cache on phone

---

## Common Tasks

### Add New Slab Manually

**Via Admin Interface:**
1. Open http://localhost:8000/admin
2. Click "Add New Slab"
3. Fill in details:
   - Name (required)
   - Stone type
   - Supplier
   - Finish
   - Dimensions
   - Location
   - Upload image (optional)
4. Click "Create"
5. QR code generated automatically

**Via API:**
```bash
curl -X POST http://localhost:8000/api/v1/slabs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Carrara Marble",
    "stone_type": "Marble",
    "supplier": "Italian Imports",
    "finish": "Polished",
    "thickness": 1.25,
    "length": 120,
    "width": 75,
    "location": "A-1"
  }'
```

### Update Slab Information

**Via Admin Interface:**
1. Find slab in admin list
2. Click "Edit"
3. Update fields
4. Click "Save"

**Via API:**
```bash
curl -X PUT http://localhost:8000/api/v1/slabs/aB3x9Km2 \
  -H "Content-Type: application/json" \
  -d '{
    "location": "B-5",
    "status": "sold"
  }'
```

### Delete Slab

**Via Admin Interface:**
1. Find slab in list
2. Click "Delete"
3. Confirm deletion

**Via API:**
```bash
curl -X DELETE http://localhost:8000/api/v1/slabs/aB3x9Km2
```

**Note:** Deletion is permanent. Consider marking as "sold" instead.

### Search and Filter Slabs

**Via Admin Interface:**
- Use search box for name/type
- Filter by status, type, location
- Sort by date, name, etc.

**Via API:**
```bash
# Search by name
curl "http://localhost:8000/api/v1/slabs?search=Calacatta"

# Filter by stone type
curl "http://localhost:8000/api/v1/slabs?stone_type=Marble"

# Filter by location
curl "http://localhost:8000/api/v1/slabs?location=A-1"

# Pagination
curl "http://localhost:8000/api/v1/slabs?skip=0&limit=20"
```

### Export Slab Data

**Method 1: Via Database Query**
```bash
# Install SQLite command-line tool
# Then export to CSV:
sqlite3 data/slabhub.db

.headers on
.mode csv
.output slabs_export.csv
SELECT * FROM slabs;
.quit
```

**Method 2: Via Python Script**
```python
from backend.app.models import SessionLocal, Slab
import json

db = SessionLocal()
slabs = db.query(Slab).all()

export_data = []
for slab in slabs:
    export_data.append({
        'public_id': slab.public_id,
        'name': slab.name,
        'stone_type': slab.stone_type,
        'supplier': slab.supplier,
        'location': slab.location,
        # Add more fields as needed
    })

with open('slabs_export.json', 'w') as f:
    json.dump(export_data, f, indent=2)

db.close()
print(f"Exported {len(export_data)} slabs")
```

### Regenerate All QR Codes

```python
from backend.app.models import SessionLocal, Slab
from backend.app.utils.qr_generator import generate_qr_code

db = SessionLocal()
slabs = db.query(Slab).all()

for slab in slabs:
    try:
        qr_path = generate_qr_code(slab.public_id)
        slab.qr_code_path = str(qr_path)
        print(f"Generated: {slab.public_id}")
    except Exception as e:
        print(f"Failed {slab.public_id}: {e}")

db.commit()
db.close()
print("Done!")
```

---

## Monitoring and Logs

### Log Files

**Main Application Log:**
```
data/logs/slabhub.log
```

Contains:
- Service startup/shutdown
- Import processing
- Watch folder activity
- Errors and warnings
- API requests (if debug enabled)

**Import Logs:**
- Stored in database (import_logs table)
- Accessible via admin interface
- Contains import statistics and errors

### Viewing Logs

**Real-Time Monitoring (Windows PowerShell):**
```powershell
Get-Content data\logs\slabhub.log -Wait
```

**Real-Time Monitoring (Command Prompt):**
```bash
# Requires tail.exe (from Git for Windows or similar)
tail -f data/logs/slabhub.log
```

**View Recent Logs:**
```bash
# Last 100 lines
Get-Content data\logs\slabhub.log -Tail 100

# Or
type data\logs\slabhub.log | more
```

**Search Logs:**
```bash
# Find errors
type data\logs\slabhub.log | findstr "ERROR"

# Find warnings
type data\logs\slabhub.log | findstr "WARNING"

# Find specific slab
type data\logs\slabhub.log | findstr "aB3x9Km2"

# Find imports
type data\logs\slabhub.log | findstr "import"
```

### Log Levels

Configure in `.env`:
```env
LOG_LEVEL=INFO
```

Options:
- `DEBUG`: Very verbose, includes all details
- `INFO`: Normal operations (recommended)
- `WARNING`: Warnings and errors only
- `ERROR`: Errors only
- `CRITICAL`: Critical errors only

### Log Rotation

**Manual Rotation:**
```bash
# Rename current log
rename data\logs\slabhub.log slabhub_20260110.log

# Restart service (creates new log)
python scripts/start_services.py
```

**Automatic Rotation:**

Create `scripts/rotate_logs.bat`:
```batch
@echo off
set DATE=%date:~-4,4%%date:~-10,2%%date:~-7,2%
rename C:\SlabHub\data\logs\slabhub.log slabhub_%DATE%.log

REM Delete logs older than 30 days
forfiles /p "C:\SlabHub\data\logs" /m slabhub_*.log /d -30 /c "cmd /c del @path"
```

Schedule with Task Scheduler (run weekly).

### Monitoring System Health

**Health Check Endpoint:**
```bash
curl http://localhost:8000/health
```

Response includes:
- Overall status
- Database connection status
- Watch folder status
- Configuration details

**Automated Monitoring:**

Create `scripts/health_check.bat`:
```batch
@echo off
curl -s http://localhost:8000/health > health.json
type health.json | findstr "healthy"
if errorlevel 1 (
    echo ALERT: SlabHub is unhealthy!
    REM Send notification or restart service
) else (
    echo OK: SlabHub is healthy
)
```

Run periodically with Task Scheduler.

---

## Database Operations

### Database Location

```
C:\SlabHub\data\slabhub.db
```

SQLite database file containing all slab data.

### Backup Database

**Manual Backup:**
```bash
# Simple copy
copy data\slabhub.db data\backups\slabhub_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db

# Verify backup
dir data\backups\
```

**Automated Backup Script:**

See `scripts/backup.bat` in DEPLOYMENT.md

**Before Major Changes:**
```bash
# Always backup before:
# - Database schema changes
# - Large imports
# - Bulk updates/deletes
# - Version upgrades

copy data\slabhub.db data\backups\slabhub_before_import.db
```

### Restore Database

**From Backup:**
```bash
# Stop SlabHub first!
# Press Ctrl+C to stop service

# Restore backup
copy data\backups\slabhub_YYYYMMDD.db data\slabhub.db

# Restart service
python scripts/start_services.py
```

### Database Queries

**Using SQLite Command Line:**
```bash
# Install sqlite3 (comes with Python)
# Or download from: https://www.sqlite.org/download.html

# Open database
sqlite3 data/slabhub.db

# Run queries
SELECT COUNT(*) FROM slabs;
SELECT * FROM slabs WHERE status = 'available';
SELECT stone_type, COUNT(*) FROM slabs GROUP BY stone_type;

# Exit
.quit
```

**Common Queries:**

Count slabs:
```sql
SELECT COUNT(*) as total_slabs FROM slabs;
```

Slabs by type:
```sql
SELECT stone_type, COUNT(*) as count
FROM slabs
GROUP BY stone_type
ORDER BY count DESC;
```

Available slabs:
```sql
SELECT public_id, name, stone_type, location
FROM slabs
WHERE status = 'available'
ORDER BY created_at DESC;
```

Recent imports:
```sql
SELECT * FROM import_logs
ORDER BY started_at DESC
LIMIT 10;
```

Duplicate hashes:
```sql
SELECT perceptual_hash, COUNT(*) as count
FROM slabs
WHERE perceptual_hash IS NOT NULL
GROUP BY perceptual_hash
HAVING count > 1;
```

### Database Maintenance

**Vacuum (Reclaim Space):**
```bash
sqlite3 data/slabhub.db "VACUUM;"
```

**Analyze (Update Statistics):**
```bash
sqlite3 data/slabhub.db "ANALYZE;"
```

**Check Integrity:**
```bash
sqlite3 data/slabhub.db "PRAGMA integrity_check;"
```

**Optimize (Both):**
```bash
sqlite3 data/slabhub.db "VACUUM; ANALYZE;"
```

Run monthly or after large imports/deletions.

---

## Maintenance Procedures

### Daily Maintenance

**Morning:**
- [ ] Start services
- [ ] Check health endpoint
- [ ] Review overnight logs for errors
- [ ] Verify watch folder is running

**Evening:**
- [ ] Review day's imports
- [ ] Check for errors in logs
- [ ] Run backup (optional for daily)
- [ ] Stop services (optional)

### Weekly Maintenance

**Every Monday:**
```bash
# Backup database
scripts\backup.bat

# Check disk space
dir C:\

# Review logs for patterns
type data\logs\slabhub.log | findstr "ERROR" > weekly_errors.txt

# Clean old logs
scripts\rotate_logs.bat

# Test system
python scripts\test_system.py
```

### Monthly Maintenance

**First of Month:**
1. **Full Backup:**
   ```bash
   # Backup entire data directory
   xcopy data data_backup_%date:~-4,4%%date:~-10,2%\ /E /I
   ```

2. **Database Maintenance:**
   ```bash
   sqlite3 data/slabhub.db "VACUUM; ANALYZE;"
   ```

3. **Archive Old Logs:**
   ```bash
   mkdir data\logs\archive\%date:~-4,4%%date:~-10,2%
   move data\logs\slabhub_*.log data\logs\archive\%date:~-4,4%%date:~-10,2%\
   ```

4. **Review Statistics:**
   - Total slabs
   - Imports this month
   - QR code scans (if tracked)
   - Storage usage

5. **Update Dependencies (if needed):**
   ```bash
   pip list --outdated
   # Review and update carefully
   ```

### Quarterly Maintenance

**Every 3 Months:**
1. **Full System Review:**
   - Review all configuration
   - Update documentation
   - Check for software updates
   - Review security settings

2. **Performance Optimization:**
   - Analyze slow queries
   - Review image storage
   - Check disk usage trends
   - Optimize if needed

3. **Disaster Recovery Test:**
   - Test backup restoration
   - Verify rollback procedures
   - Update emergency contacts

---

## Common Issues and Fixes

### Service Won't Start

**Symptom:** `python scripts/start_services.py` fails

**Quick Fix:**
```bash
# Check if port in use
netstat -ano | findstr :8000

# Kill process if found
taskkill /PID <process_id> /F

# Restart
python scripts/start_services.py
```

**Root Cause Analysis:**
1. Check virtual environment activated
2. Verify all dependencies installed
3. Check `.env` file exists and valid
4. Review logs for specific error
5. Verify database file exists

### Images Not Being Imported

**Symptom:** Images in SlabCrop folder aren't imported

**Quick Fix:**
```bash
# Restart watch folder
# Stop service (Ctrl+C)
# Start service
python scripts/start_services.py

# Check logs
type data\logs\slabhub.log | findstr "watch"
```

**Checklist:**
- [ ] Watch folder enabled in `.env`
- [ ] SlabCrop path correct
- [ ] Image format supported (jpg, png)
- [ ] Image meets size requirements
- [ ] No permission issues on folder
- [ ] Service is running

### QR Codes Not Working

**Symptom:** Scanning QR code doesn't load page

**Quick Fix:**
```bash
# Verify PUBLIC_BASE_URL
python -c "from backend.app.config import settings; print(settings.public_base_url)"

# Test URL manually
# Open http://192.168.1.100:8000/health in phone browser
```

**Checklist:**
- [ ] PUBLIC_BASE_URL matches server IP
- [ ] Phone on same Wi-Fi network
- [ ] Firewall allows connections
- [ ] Service is running
- [ ] URL in QR code is correct

### Database Locked

**Symptom:** "database is locked" error

**Quick Fix:**
```bash
# Stop all SlabHub processes
taskkill /IM python.exe /F

# Wait 5 seconds
timeout /t 5

# Restart
python scripts/start_services.py
```

**Prevention:**
- Don't open database in multiple applications
- Use proper shutdown (Ctrl+C)
- Ensure writes are committed

### Slow Performance

**Symptom:** Pages load slowly, operations timeout

**Quick Fix:**
```bash
# Optimize database
sqlite3 data/slabhub.db "VACUUM; ANALYZE;"

# Restart service
# (Ctrl+C, then restart)
```

**Investigation:**
1. Check disk space
2. Review log file size
3. Check CPU/RAM usage in Task Manager
4. Count database records
5. Review for large images

### Printer Not Printing

**Symptom:** Labels won't print

**Quick Fix:**
1. Check printer is online in Windows
2. Print test page from Windows
3. Regenerate label PDF
4. Try printing PDF manually

**Checklist:**
- [ ] Printer driver installed
- [ ] Printer online and connected
- [ ] Thermal paper loaded correctly
- [ ] USB/Bluetooth connection stable
- [ ] Label size correct (4x6")

---

## Emergency Procedures

### System Down

**Immediate Actions:**
1. Check if service is running
2. Review last 50 lines of log
3. Attempt restart
4. If fails, restore from backup
5. Notify users of downtime

### Data Corruption

**Immediate Actions:**
1. Stop service immediately
2. Backup current database (even if corrupted)
3. Check integrity:
   ```bash
   sqlite3 data/slabhub.db "PRAGMA integrity_check;"
   ```
4. If corrupted, restore from backup:
   ```bash
   copy data\backups\slabhub_latest.db data\slabhub.db
   ```
5. Restart service
6. Verify functionality

### Network Issues

**Immediate Actions:**
1. Check IP address unchanged:
   ```bash
   ipconfig
   ```
2. Update PUBLIC_BASE_URL if changed
3. Restart service
4. Test from multiple devices
5. Check firewall rules

---

## Getting Help

### Self-Service Resources

1. **This Runbook**: Common tasks and issues
2. **DEPLOYMENT.md**: Installation and configuration
3. **README.md**: Project overview
4. **Logs**: `data/logs/slabhub.log`
5. **Health Endpoint**: http://localhost:8000/health
6. **API Docs**: http://localhost:8000/docs

### Contact Support

If issues persist:
1. Gather information:
   - Error messages
   - Log excerpts
   - Steps to reproduce
   - Recent changes
2. Check documentation again
3. Contact system administrator
4. Include log files and health check output

---

## Appendix

### Useful Commands Reference

**Service Control:**
```bash
# Start
python scripts/start_services.py

# Stop
# Press Ctrl+C

# Restart
# Stop, then start
```

**Health Checks:**
```bash
curl http://localhost:8000/health
```

**Logs:**
```bash
# View
type data\logs\slabhub.log

# Monitor
Get-Content data\logs\slabhub.log -Wait

# Search
type data\logs\slabhub.log | findstr "ERROR"
```

**Database:**
```bash
# Backup
copy data\slabhub.db data\backups\slabhub_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db

# Query
sqlite3 data/slabhub.db "SELECT COUNT(*) FROM slabs;"

# Optimize
sqlite3 data/slabhub.db "VACUUM; ANALYZE;"
```

**Import:**
```bash
# Dry run
python scripts/import_metadata.py --file data.json --dry-run

# Import
python scripts/import_metadata.py --file data.json
```

### Configuration Quick Reference

**Key .env Variables:**
```env
PUBLIC_BASE_URL=http://192.168.1.100:8000
SLABCROP_OUTPUT_FOLDER=D:/SlabCrop/output
ENABLE_WATCH_FOLDER=true
DATABASE_URL=sqlite:///./data/slabhub.db
LOG_LEVEL=INFO
```

### File Locations Quick Reference

```
C:\SlabHub\
├── .env                          # Configuration
├── data\
│   ├── slabhub.db               # Database
│   ├── logs\slabhub.log         # Main log
│   ├── labels\                  # Generated labels
│   ├── qr\                      # QR codes
│   ├── archive\                 # Processed images
│   └── backups\                 # Database backups
├── scripts\
│   ├── start_services.py        # Start script
│   ├── test_system.py           # Test script
│   └── import_metadata.py       # Import script
└── venv\                        # Virtual environment
```

---

This runbook should be your daily reference for operating SlabHub. Keep it updated with your site-specific procedures and customizations.
