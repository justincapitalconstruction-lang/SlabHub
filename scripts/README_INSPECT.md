# Stone Identifications Inspector

## Overview

`inspect_stone_identifications.py` is a utility script for analyzing the structure and schema of stone metadata JSON files before importing them into SlabHub.

## Purpose

- **Debug import issues** - Understand why JSON imports might be failing
- **Schema analysis** - See what fields are present in your data
- **Data validation** - Check types and structure before bulk import
- **Quick preview** - View sample entries without importing

## Installation

✅ Already installed at: `scripts/inspect_stone_identifications.py`

No additional dependencies required (uses Python standard library only).

## Usage

### Basic Inspection

```bash
python scripts/inspect_stone_identifications.py --path path/to/stone-identifications.json
```

### With Multiple Samples

```bash
python scripts/inspect_stone_identifications.py --path data.json --sample 3
```

### Common Use Cases

```bash
# Inspect the example file (if you have one)
python scripts/inspect_stone_identifications.py --path data/imports/stone-identifications.json

# Check a downloaded file
python scripts/inspect_stone_identifications.py --path D:/downloads/stones.json --sample 5

# Analyze Sortly export
python scripts/inspect_stone_identifications.py --path D:/sortly-export.json
```

## Supported JSON Formats

The script automatically detects and handles multiple JSON structures:

### Format 1: List of Objects
```json
[
  {"id": 1, "name": "Calacatta Gold", "stone_type": "Marble"},
  {"id": 2, "name": "Black Galaxy", "stone_type": "Granite"}
]
```

### Format 2: Object with 'items' Key
```json
{
  "items": [
    {"id": 1, "name": "Calacatta Gold"},
    {"id": 2, "name": "Black Galaxy"}
  ]
}
```

### Format 3: ID-to-Entry Mapping
```json
{
  "1": {"name": "Calacatta Gold", "stone_type": "Marble"},
  "2": {"name": "Black Galaxy", "stone_type": "Granite"}
}
```

## Output Example

```
Top-level type: list
Detected entries: 156

Most common keys:
  name: 156  types={'str': 156}
  stone_type: 156  types={'str': 156}
  color: 156  types={'str': 155, 'null': 1}
  finish: 150  types={'str': 150}
  features: 140  types={'str': 140}
  supplier: 120  types={'str': 120}
  price: 100  types={'num': 100}
  image_filename: 156  types={'str': 156}

Sample entries:

--- SAMPLE 1 ---
{
  "name": "Calacatta Gold Premium",
  "stone_type": "Marble",
  "color": "White with Gold Veining",
  "finish": "Polished",
  "features": "Dramatic gold veining, high contrast",
  "supplier": "Italian Stone Co.",
  "price": 4200.0,
  "image_filename": "calacatta-gold-001.jpg"
}

=============================================================
SUMMARY
=============================================================
Total entries: 156
Total unique keys: 15
Most common key: name
```

## Integration with Import Scripts

Use this inspector BEFORE running imports to:

1. **Check field mappings** - See what fields are available
2. **Verify data quality** - Check for missing or null values
3. **Plan import strategy** - Understand what metadata you'll get
4. **Debug failures** - Compare expected vs. actual structure

### Workflow Example

```bash
# Step 1: Inspect the JSON file
python scripts/inspect_stone_identifications.py --path data.json --sample 3

# Step 2: Review output, check field names

# Step 3: Run import (adjust field mappings if needed)
python scripts/import_metadata.py --file data.json --dry-run

# Step 4: If dry-run looks good, execute
python scripts/import_metadata.py --file data.json
```

## Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--path` | Yes | - | Path to JSON file to inspect |
| `--sample` | No | 1 | Number of sample entries to print |

## Error Handling

The script handles common errors gracefully:

- **File not found** - Shows clear error message
- **Invalid JSON** - Reports JSON parsing errors
- **Empty/invalid structure** - Warns if no entries detected
- **Wrong file type** - Shows JSON decode error for non-JSON files

## Examples

### Example 1: Quick Check
```bash
python scripts/inspect_stone_identifications.py --path stones.json
```

### Example 2: Deep Analysis
```bash
python scripts/inspect_stone_identifications.py --path stones.json --sample 10
```

### Example 3: Sortly Export
```bash
# If you exported from Sortly
python scripts/inspect_stone_identifications.py --path sortly-export-2026.json --sample 5
```

## Troubleshooting

### "No entries detected"
- Check JSON structure matches one of the supported formats
- Verify file contains actual data (not empty array/object)
- Try opening the file in a JSON viewer to check structure

### "Invalid JSON"
- File might be CSV, not JSON
- File might be corrupted
- Check for syntax errors (missing commas, brackets)

### "File not found"
- Check path is correct
- Use absolute path if relative path doesn't work
- Check file permissions

## Compatibility

- ✅ **Python Version:** 3.7+ (uses `from __future__ import annotations`)
- ✅ **Dependencies:** None (standard library only)
- ✅ **Operating Systems:** Windows, macOS, Linux
- ✅ **Conflicts:** None - standalone utility script

## Related Scripts

- `scripts/import_metadata.py` - Import from JSON metadata files
- `scripts/import_csv.py` - Import from CSV files
- `scripts/verify_import.py` - Verify imported data

## Notes

- This is a **read-only** inspection tool - it never modifies your data
- Safe to run multiple times on the same file
- Useful for understanding third-party exports (Sortly, Excel, etc.)
- Can handle large files (streams entries one at a time)

---

**Location:** `c:\Users\Justi\.zenflow\worktrees\new-task-4426\scripts\inspect_stone_identifications.py`
