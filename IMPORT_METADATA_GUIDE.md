# SlabHub Metadata Import - Complete Guide

## Overview

The `import_metadata.py` script provides a robust, production-ready solution for importing stone slab data from JSON files into SlabHub. It handles field mapping, type conversion, duplicate detection, QR code generation, and comprehensive logging.

## Quick Start

```bash
# 1. Initialize database (first time only)
python scripts/init_db.py

# 2. Test import with dry run
python scripts/import_metadata.py --file data/imports/stone-identifications.json --dry-run

# 3. Run actual import
python scripts/import_metadata.py --file data/imports/stone-identifications.json

# 4. Verify results
python scripts/verify_import.py
```

## Files Created

- **`C:\Users\Justi\.zenflow\worktrees\new-task-4426\scripts\import_metadata.py`** - Main import script (743 lines)
- **`C:\Users\Justi\.zenflow\worktrees\new-task-4426\scripts\init_db.py`** - Database initialization helper
- **`C:\Users\Justi\.zenflow\worktrees\new-task-4426\scripts\verify_import.py`** - Import verification helper
- **`C:\Users\Justi\.zenflow\worktrees\new-task-4426\scripts\README_IMPORT.md`** - Detailed documentation
- **`C:\Users\Justi\.zenflow\worktrees\new-task-4426\data\imports\stone-identifications-sample.json`** - Sample data

## Features Implemented

### 1. Field Mapping System
Automatically maps 40+ field name variations to Slab model fields:

```python
# Example mappings:
"name" ← name, title, description, slab_name, identifier
"stone_type" ← stone_type, type, material, stone, material_type
"supplier" ← supplier, vendor, source, provider
"finish" ← finish, surface, surface_finish, treatment
"location" ← location, warehouse_location, storage_location
"tags" ← tags, categories, labels
```

### 2. Smart Data Processing

**Type Conversion:**
- Strings to floats (thickness: "3.0" → 3.0)
- Strings to integers (quantity: "5" → 5)
- Removes commas and quotes from numbers
- Handles empty/null values gracefully

**Dimension Parsing:**
```json
"dimensions": "120x80"  → length: 120.0, width: 80.0
```

**Tags Processing:**
```json
// Array format
"tags": ["premium", "marble"]  → "premium, marble"

// String format
"tags": "premium,marble,italian"  → "premium, marble, italian"
```

### 3. Unique ID Generation
- Generates 8-character alphanumeric public IDs
- Base62 encoding (0-9, a-z, A-Z)
- Ensures uniqueness in database
- Example: `aB3x9Km2`, `oGwVafJ1`

### 4. Perceptual Hash Calculation
- Calculates image hashes for duplicate detection
- Uses average hash algorithm (resistant to scaling)
- 64-bit hash (8x8 grid)
- Stores hash in database for future comparisons

### 5. Duplicate Detection

**By Public ID:**
- Checks if public_id already exists
- Skips item if duplicate found

**By Perceptual Hash:**
- Compares image similarity using Hamming distance
- Configurable threshold (default: 10 bits)
- Detects visually similar images
- Prevents duplicate imports

### 6. QR Code Generation
- Automatically generates QR codes for each slab
- Format: `{base_url}/s/{public_id}`
- Saved as PNG to `data/qr/{public_id}.png`
- 10 pixels per module, 4-module border
- Error correction level: L (~7%)

### 7. Flexible Data Storage

**Mapped Fields:**
Standard fields are mapped to Slab model columns

**Unmapped Fields:**
Any fields not in mapping are preserved in `extra_json`:
```json
{
  "hardness": "7 Mohs",
  "origin": "Italy",
  "certification": "CE Marked"
}
```

### 8. Import Tracking

**ImportLog Record:**
Each batch creates a database record with:
- Batch ID (unique 16-character ID)
- Import type: `json_metadata`
- Source file path
- Status: completed/partial/failed
- Statistics (processed, success, failed, skipped)
- Error and warning arrays
- Timing information
- Summary text

### 9. Progress Display

**Console Output:**
```
INFO: Progress: 10/50
INFO: Progress: 20/50
INFO: Item 25/50: Successfully imported - Calacatta Gold (aB3x9Km2)
```

**Summary Report:**
```
============================================================
Metadata Import Summary
Batch ID: GAzTBycduFxZrQFm
Total Processed: 5
Successful: 5
Failed: 0
Skipped (Duplicates): 0
Success Rate: 100.0%
============================================================

Warnings (5):
  - Item 1: Image file not found: ...
  - Item 2: Failed to calculate hash: ...
```

### 10. Comprehensive Logging

**Console Output:**
- INFO level messages
- Progress updates
- Warnings and errors
- Summary report

**File Logging:**
- DEBUG level details
- Full stack traces
- Timestamped entries
- Saved to: `data/logs/import_metadata_{timestamp}.log`

### 11. Error Handling

**Per-Item Errors:**
- Script continues processing on errors
- Failed items logged with details
- Database rolled back for failed items
- Other items still imported

**Error Types Handled:**
- Missing required fields
- Type conversion failures
- File not found (images)
- Database errors
- QR generation failures
- Hash calculation failures

### 12. Dry Run Mode

**Features:**
- Preview without database changes
- Validates JSON structure
- Tests field mapping
- Shows what would be imported
- No QR code generation
- No ImportLog created

**Usage:**
```bash
python scripts/import_metadata.py --file test.json --dry-run
```

## CLI Arguments

```bash
python scripts/import_metadata.py [OPTIONS]

Options:
  --file FILE    Path to JSON file (default: settings.import_metadata_file)
  --dry-run      Preview without inserting into database
  -h, --help     Show help message
```

## Configuration Options

**In `.env` or `backend/app/config.py`:**

```python
# Default import file
import_metadata_file = "./data/imports/stone-identifications.json"

# Duplicate detection threshold (0-64, lower = stricter)
duplicate_threshold = 10

# QR code output folder
qr_output_folder = "./data/qr"

# Public base URL for QR codes
public_base_url = "http://localhost:8000"

# Database URL
database_url = "sqlite:///./data/slabhub.db"

# Log level
log_level = "INFO"
```

## JSON Format Examples

### Minimal Example
```json
{
  "name": "Calacatta Gold"
}
```

### Standard Example
```json
{
  "name": "Calacatta Gold Premium",
  "type": "Marble",
  "supplier": "Italian Stone Co.",
  "finish": "Polished",
  "thickness": "3.0",
  "dimensions": "120x80",
  "location": "Warehouse A-12",
  "status": "available",
  "tags": ["premium", "marble", "italian"],
  "image": "./data/images/calacatta-gold-001.jpg",
  "cost": 2500.00,
  "price": 4200.00
}
```

### Complex Example with Extra Fields
```json
{
  "name": "Fantasy Brown Quartzite",
  "stone_type": "Quartzite",
  "supplier": "Brazil Stone Imports",
  "finish": "Polished",
  "thickness": 2.5,
  "color": "Brown with Cream Veining",
  "length": 126,
  "width": 75,
  "location": "Warehouse C-3",
  "status": "available",
  "quantity": 1,
  "tags": ["quartzite", "brown", "exotic"],
  "notes": "Rare pattern, single slab available",
  "primary_image": "./data/images/fantasy-brown-004.jpg",
  "cost": 3200.00,
  "price": 5400.00,
  "hardness": "7 Mohs",
  "sealant_required": true,
  "origin": "Brazil",
  "certification": "CE Marked"
}
```

Result in database:
- Standard fields: Mapped to columns
- Extra fields: `{"hardness": "7 Mohs", "sealant_required": true, "origin": "Brazil", "certification": "CE Marked"}`

## Test Results

**Sample Import Test:**
- 5 items processed
- 100% success rate
- 5 QR codes generated
- 1 ImportLog created
- All fields correctly mapped
- Extra fields preserved in `extra_json`
- Warnings for missing image files (expected)

**Files Created:**
```
data/qr/oGwVafJ1.png (549 bytes)
data/qr/DZJuO9Bm.png (560 bytes)
data/qr/2dnJts6H.png (554 bytes)
data/qr/R6giPA0Z.png (579 bytes)
data/qr/H3R7b4So.png (538 bytes)
data/logs/import_metadata_20260110_234007.log (3.8 KB)
```

## Database Schema Integration

The script integrates seamlessly with the Slab model:

**Mapped Fields:**
- `public_id` - Generated unique ID
- `name` - Required field
- `stone_type`, `supplier`, `finish`, `color`, `location`, `status`
- `thickness`, `length`, `width`, `square_feet`
- `quantity`, `cost`, `price`
- `tags`, `notes`
- `primary_image`, `additional_images`
- `import_source` - Set to 'json_metadata'
- `import_batch_id` - Batch tracking ID
- `perceptual_hash` - Image hash for duplicates
- `qr_code_path` - Path to QR code PNG
- `extra_json` - Unmapped fields

**Automatic Fields:**
- `created_at`, `updated_at` - Timestamps
- `id` - Auto-increment primary key

## Best Practices

1. **Always test with --dry-run first**
   ```bash
   python scripts/import_metadata.py --file new-data.json --dry-run
   ```

2. **Backup database before large imports**
   ```bash
   cp data/slabhub.db data/slabhub.db.backup
   ```

3. **Review logs after import**
   ```bash
   tail -f data/logs/import_metadata_*.log
   ```

4. **Verify import results**
   ```bash
   python scripts/verify_import.py
   ```

5. **Use descriptive filenames**
   - `stone-identifications-2024-q1.json`
   - `inventory-import-warehouse-a.json`

## Production Deployment

1. **Set environment variables:**
   ```bash
   export import_metadata_file="/path/to/stone-identifications.json"
   export database_url="postgresql://user:pass@host/db"
   export public_base_url="https://yourdomain.com"
   ```

2. **Run import:**
   ```bash
   python scripts/import_metadata.py
   ```

3. **Monitor logs:**
   ```bash
   tail -f data/logs/import_metadata_*.log
   ```

4. **Schedule regular imports (optional):**
   ```bash
   # Cron job example (daily at 2 AM)
   0 2 * * * cd /path/to/slabhub && python scripts/import_metadata.py
   ```

## Troubleshooting

### "File not found" Error
**Cause:** JSON file doesn't exist
**Solution:** Check file path, use absolute path if needed

### "No input file specified" Error
**Cause:** No --file argument and no settings.import_metadata_file
**Solution:** Use --file or set import_metadata_file in settings

### "Missing required field 'name'" Error
**Cause:** Item has no name/title/description field
**Solution:** Add name field or use alternative (title, description, etc.)

### "Image file not found" Warnings
**Cause:** Image path in JSON doesn't exist
**Solution:** Update image paths or ignore (slab still imported)

### "Failed to generate QR code" Warnings
**Cause:** QR output folder not writable
**Solution:** Check folder permissions, create folder manually

### Database Errors
**Cause:** Database not initialized or locked
**Solution:** Run `python scripts/init_db.py` first

## Advanced Usage

### Programmatic Import
```python
from scripts.import_metadata import MetadataImporter
from pathlib import Path

importer = MetadataImporter(dry_run=False)
exit_code = importer.run(Path("data/imports/my-data.json"))

if exit_code == 0:
    print("Import successful!")
    print(f"Processed: {importer.stats['processed']}")
    print(f"Success: {importer.stats['success']}")
```

### Batch Processing
```bash
for file in data/imports/*.json; do
    echo "Importing $file..."
    python scripts/import_metadata.py --file "$file"
done
```

### Custom Field Mapping
Modify `FieldMapper.FIELD_MAPPINGS` in the script to add custom mappings.

## Support & Documentation

- **Main Documentation:** `scripts/README_IMPORT.md`
- **Sample Data:** `data/imports/stone-identifications-sample.json`
- **Database Schema:** `DATABASE_SCHEMA.md`
- **Models Reference:** `MODELS_QUICK_REFERENCE.md`

## Summary

The metadata importer is a **production-ready, standalone script** that:

✅ Handles flexible JSON input (single object or array)
✅ Maps 40+ field name variations automatically
✅ Converts data types intelligently
✅ Parses dimension strings
✅ Generates unique public IDs
✅ Calculates perceptual hashes
✅ Detects duplicates (by ID and image)
✅ Generates QR codes automatically
✅ Preserves unmapped fields
✅ Creates ImportLog records
✅ Shows progress and summary
✅ Handles errors gracefully
✅ Provides dry-run mode
✅ Logs comprehensively (console + file)
✅ Integrates with existing SlabHub models and utilities

**Ready for immediate use in production!**
