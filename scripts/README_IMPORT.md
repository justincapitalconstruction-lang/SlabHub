# SlabHub Metadata Importer

Standalone script to import stone slab data from JSON files (e.g., `stone-identifications.json`).

## Quick Start

```bash
# Import from default file (set in settings.import_metadata_file)
python scripts/import_metadata.py

# Import from custom file
python scripts/import_metadata.py --file data/imports/stone-identifications.json

# Preview import without saving (dry run)
python scripts/import_metadata.py --dry-run

# Preview custom file
python scripts/import_metadata.py --file custom.json --dry-run
```

## Features

### Automatic Field Mapping
The script intelligently maps various field name variations to the Slab model:

| Slab Field | Recognized Variations |
|------------|----------------------|
| `name` | name, title, description, slab_name, identifier |
| `stone_type` | stone_type, type, material, stone, material_type |
| `supplier` | supplier, vendor, source, provider |
| `finish` | finish, surface, surface_finish, treatment |
| `thickness` | thickness, thick |
| `color` | color, colour, primary_color |
| `location` | location, warehouse_location, storage_location, warehouse |
| `status` | status, state, availability |
| `tags` | tags, categories, labels |
| `notes` | notes, description, comments, memo |
| `primary_image` | primary_image, image, image_path, photo, picture, main_image |
| `cost` | cost, purchase_price, cost_price |
| `price` | price, selling_price, sale_price, retail_price |

### Smart Data Processing

1. **Type Conversion**
   - Automatically converts string numbers to floats/integers
   - Handles comma-separated tags and arrays
   - Parses dimension strings like "120x80" into length/width

2. **Public ID Generation**
   - Generates unique 8-character alphanumeric IDs
   - Ensures uniqueness in database
   - Used for QR codes and URLs

3. **Perceptual Hash Calculation**
   - Calculates image hashes for duplicate detection
   - Compares against existing slabs
   - Configurable similarity threshold

4. **Duplicate Detection**
   - Checks for duplicate public IDs
   - Image-based duplicate detection via perceptual hashing
   - Skips duplicates automatically

5. **QR Code Generation**
   - Automatically generates QR codes for each slab
   - Saved to configured output folder
   - Links to public slab URL

6. **Flexible Storage**
   - Unmapped fields stored in `extra_json` column
   - No data loss - everything is preserved
   - Easy to query custom fields later

## JSON Format

The script accepts both single objects and arrays of objects:

### Single Object
```json
{
  "name": "Calacatta Gold",
  "type": "Marble",
  "supplier": "Italian Stone Co.",
  "finish": "Polished",
  "thickness": "3.0",
  "dimensions": "120x80",
  "location": "Warehouse A-12",
  "status": "available",
  "tags": ["premium", "marble"],
  "image": "./data/images/calacatta.jpg",
  "cost": 2500.00,
  "price": 4200.00
}
```

### Array of Objects
```json
[
  {
    "name": "Calacatta Gold",
    "type": "Marble",
    ...
  },
  {
    "name": "Black Galaxy",
    "type": "Granite",
    ...
  }
]
```

## Field Mapping Examples

### Example 1: Standard Fields
```json
{
  "name": "Carrara White",
  "stone_type": "Marble",
  "supplier": "Tuscany Marble",
  "finish": "Honed",
  "thickness": 3,
  "location": "Warehouse A-8",
  "status": "available"
}
```

### Example 2: Alternative Field Names
```json
{
  "title": "Black Galaxy",        // Maps to name
  "material": "Granite",          // Maps to stone_type
  "vendor": "India Exports",      // Maps to supplier
  "surface": "Leathered",         // Maps to finish
  "thick": "2",                   // Maps to thickness (converted to float)
  "warehouse_location": "B-5",    // Maps to location
  "state": "available"            // Maps to status
}
```

### Example 3: Dimensions Parsing
```json
{
  "name": "Fantasy Brown",
  "dimensions": "126x75"          // Parsed into length=126, width=75
}
```

Or explicit:
```json
{
  "name": "Fantasy Brown",
  "length": 126,
  "width": 75
}
```

### Example 4: Tags as Array or String
```json
{
  "tags": ["premium", "marble", "italian"]
}
```

Or:
```json
{
  "tags": "premium,marble,italian"
}
```

Both are converted to: `"premium, marble, italian"`

### Example 5: Extra Fields Preserved
```json
{
  "name": "Absolute Black",
  "type": "Granite",
  "hardness": "7 Mohs",           // Unmapped: saved to extra_json
  "origin": "India",              // Unmapped: saved to extra_json
  "certification": "CE Marked"    // Unmapped: saved to extra_json
}
```

Result:
- Standard fields mapped normally
- `extra_json` = `{"hardness": "7 Mohs", "origin": "India", "certification": "CE Marked"}`

## Output and Logging

### Console Output
```
INFO: Logging to: data/logs/import_metadata_20260110_153045.log
INFO: Loading JSON from: data/imports/stone-identifications.json
INFO: Loaded 50 items from JSON
INFO: Progress: 10/50
INFO: Progress: 20/50
INFO: Item 25/50: Successfully imported - Calacatta Gold (aB3x9Km2)
...
============================================================
Metadata Import Summary
Batch ID: xY7mN3pQ8kL2vR9s
Total Processed: 50
Successful: 48
Failed: 1
Skipped (Duplicates): 1
Success Rate: 96.0%
============================================================
```

### Log File
Detailed logs saved to: `data/logs/import_metadata_{timestamp}.log`

Contains:
- Timestamped entries
- Debug information
- Error stack traces
- Warning details
- Full processing history

### Import Log Database
Each import creates an `ImportLog` record with:
- Batch ID
- Import type: `json_metadata`
- Source file path
- Status: completed/partial/failed
- Item counts (processed, success, failed, skipped)
- Errors and warnings (JSON arrays)
- Timing information
- Summary text

Query later:
```python
from backend.app.models import SessionLocal, ImportLog

db = SessionLocal()
recent_imports = db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(10).all()

for import_log in recent_imports:
    print(f"Batch: {import_log.batch_id}")
    print(f"Status: {import_log.status}")
    print(f"Success Rate: {import_log.get_success_rate():.1f}%")
```

## Configuration

Set default import file in `.env` or settings:

```python
# backend/app/config.py or .env
import_metadata_file = "./data/imports/stone-identifications.json"

# Duplicate detection threshold (0-64, lower = stricter)
duplicate_threshold = 10

# QR code output folder
qr_output_folder = "./data/qr"
```

## Error Handling

The script continues processing on errors:

1. **Per-Item Errors**: Logged and reported, but import continues
2. **Duplicate Detection**: Items skipped, counted separately
3. **Image Errors**: Warnings logged, but slab still imported
4. **QR Generation Errors**: Warnings logged, slab saved without QR

All errors and warnings included in:
- Console summary
- Log file
- ImportLog database record

## Dry Run Mode

Preview imports without database changes:

```bash
python scripts/import_metadata.py --file test.json --dry-run
```

Dry run:
- Validates JSON structure
- Tests field mapping
- Checks for duplicates
- Shows what would be imported
- No database changes
- No QR code generation
- No ImportLog created

## Best Practices

1. **Always test with --dry-run first**
   ```bash
   python scripts/import_metadata.py --file new-data.json --dry-run
   ```

2. **Check logs after import**
   ```bash
   tail -f data/logs/import_metadata_*.log
   ```

3. **Review import logs in database**
   ```python
   from backend.app.models import SessionLocal, ImportLog
   db = SessionLocal()
   latest = db.query(ImportLog).order_by(ImportLog.created_at.desc()).first()
   print(latest.summary)
   ```

4. **Keep backups before large imports**
   ```bash
   cp data/slabhub.db data/slabhub.db.backup
   ```

5. **Use descriptive filenames**
   ```
   stone-identifications-2024-q1.json
   inventory-import-warehouse-a.json
   ```

## Troubleshooting

### "File not found" Error
- Check file path is correct
- Use absolute path or relative to project root
- Verify file exists: `ls -l path/to/file.json`

### "No input file specified" Error
- Use `--file` argument OR
- Set `import_metadata_file` in settings/`.env`

### Missing Required Field Error
- Every item needs a `name` (or equivalent like `title`, `description`)
- Check JSON structure
- Review error in log file for specific item

### Duplicate Warnings
- Review skipped items in logs
- Adjust `duplicate_threshold` in settings if needed
- Check if duplicates are intentional

### Image Not Found Warnings
- Verify image paths in JSON
- Check paths are relative to script location or absolute
- Images can be imported later - slab still created

### QR Generation Failures
- Check `qr_output_folder` exists and is writable
- Verify sufficient disk space
- QR codes can be regenerated later

## Sample Data

See `data/imports/stone-identifications-sample.json` for examples demonstrating:
- Various field name variations
- Different data formats
- Tags as arrays and strings
- Dimension parsing
- Extra/unmapped fields

## Advanced Usage

### Custom Log Location
Modify script to change log location:
```python
setup_logging(log_file=Path("/custom/path/import.log"))
```

### Programmatic Use
```python
from scripts.import_metadata import MetadataImporter
from pathlib import Path

importer = MetadataImporter(dry_run=False)
exit_code = importer.run(Path("data/imports/my-data.json"))

if exit_code == 0:
    print("Import successful!")
    print(importer.stats)
```

### Batch Processing Multiple Files
```bash
for file in data/imports/*.json; do
    echo "Importing $file..."
    python scripts/import_metadata.py --file "$file"
done
```

## Integration with SlabHub

Imported slabs are immediately available in SlabHub:

1. **Web Interface**: Browse at `/slabs`
2. **API**: Access via `/api/slabs`
3. **QR Codes**: Scan to view slab details
4. **Search**: Full-text search on all fields
5. **Reports**: Include in inventory reports

## Support

For issues or questions:
1. Check logs in `data/logs/`
2. Review ImportLog records in database
3. Use `--dry-run` to test without changes
4. Consult documentation at docs/
