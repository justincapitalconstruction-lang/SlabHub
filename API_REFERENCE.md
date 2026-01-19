# SlabHub API Reference

**Version:** 2.07
**Last Updated:** 2026-01-18

This document provides API reference for SlabHub v2.x features introduced in Phases 2-3.

## Table of Contents

- [Overview](#overview)
- [Interactive API Documentation](#interactive-api-documentation)
- [Import API (Phase 2)](#import-api-phase-2)
- [Export API (Phase 3)](#export-api-phase-3)
- [Common Response Codes](#common-response-codes)

---

## Overview

SlabHub provides a RESTful API built with FastAPI. All API endpoints are prefixed with `/api/v1/` unless otherwise specified.

### Base URL

```
http://localhost:8000/api/v1
```

For network access, replace `localhost` with your server's IP address (configured via `PUBLIC_BASE_URL` in `.env`).

---

## Interactive API Documentation

SlabHub automatically generates interactive API documentation using Swagger UI:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

These interfaces allow you to:
- Browse all available endpoints
- View request/response schemas
- Test API calls directly from the browser
- Download the OpenAPI specification

---

## Import API (Phase 2)

### Upload Metadata File

**Endpoint:** `POST /admin/import/upload`

Uploads a CSV or XLSX file containing slab metadata. This endpoint is designed for web form submissions and returns an HTML redirect.

**Request:**
- **Method:** POST
- **Content-Type:** `multipart/form-data`
- **Body Parameter:**
  - `file` (file): CSV or XLSX file

**Supported File Formats:**
- `.csv` (UTF-8 or Latin-1 encoded)
- `.xlsx`, `.xls` (requires `openpyxl` package)

**Response:**
- **Success:** Redirects to `/admin/imports?success=<message>`
- **Partial:** Redirects to `/admin/imports?warning=<message>`
- **Error:** Redirects to `/admin/imports?error=<message>`

**Example (curl):**
```bash
curl -X POST http://localhost:8000/admin/import/upload \
  -F "file=@slabs.csv"
```

---

### Import Metadata (JSON API)

**Endpoint:** `POST /api/v1/import/metadata`

Programmatic API for importing slab metadata. Returns structured JSON response.

**Request:**
- **Method:** POST
- **Content-Type:** `multipart/form-data`
- **Body Parameter:**
  - `file` (file): CSV or XLSX file

**Response:** `ImportResult` object

```json
{
  "batch_id": "slabcrop_20260118_123456_abc123",
  "status": "completed",
  "file_type": "csv",
  "rows_processed": 100,
  "rows_imported": 95,
  "rows_updated": 5,
  "rows_failed": 0,
  "rows_skipped": 0,
  "errors": [],
  "warnings": [],
  "summary": "Import completed: 100 processed, 95 imported, 5 updated, 0 failed, 0 skipped"
}
```

**Status Values:**
- `completed` - All rows processed successfully
- `partial` - Some rows succeeded, some failed
- `failed` - No rows were imported (validation or critical error)

**Error Format:**
```json
{
  "row": 5,
  "column": "Thickness",
  "message": "Invalid number: 'abc'"
}
```

**Example (curl):**
```bash
curl -X POST http://localhost:8000/api/v1/import/metadata \
  -F "file=@slabs.xlsx" \
  -H "Accept: application/json"
```

---

### CSV/XLSX Column Mapping

SlabHub automatically maps column headers to slab fields using **case-insensitive, flexible matching**.

#### Required Columns

- **Name** (or `Title`, `Slab_Name`) - Slab identifier/name

#### Optional Columns

| CSV Header(s) | Slab Field | Type | Description |
|---------------|------------|------|-------------|
| `SlabID`, `Slab_ID`, `ID` | `public_id` | String | Unique identifier (if present, updates existing slab) |
| `Name`, `Title`, `Slab_Name` | `name` | String | Slab name (required) |
| `StoneType`, `Type`, `Material` | `stone_type` | String | Type of stone |
| `Supplier`, `Vendor` | `supplier` | String | Supplier name |
| `Finish`, `Surface` | `finish` | String | Surface finish |
| `Thickness`, `Thick` | `thickness` | Float | Thickness in inches |
| `Color`, `Colour` | `color` | String | Primary color |
| `Length`, `Len` | `length` | Float | Length in inches |
| `Width`, `W` | `width` | Float | Width in inches |
| `SquareFeet`, `SqFt`, `Area` | `square_feet` | Float | Total square footage |
| `Location`, `Warehouse`, `Storage` | `location` | String | Storage location |
| `Status`, `State` | `status` | String | Status (available, reserved, sold, etc.) |
| `Quantity`, `Qty` | `quantity` | Integer | Number of identical slabs |
| `Cost`, `CostPrice` | `cost` | Float | Cost price |
| `Price`, `SellingPrice` | `price` | Float | Selling price |
| `Tags`, `Categories` | `tags` | String | Comma-separated tags |
| `Notes`, `Comments`, `Description` | `notes` | String | Internal notes |

**Unmapped Columns:**
Any column not recognized above will be stored in the `extra_json` field for later retrieval.

---

### Validation Rules

**Header Validation:**
- At least one column must map to `name`
- Missing required columns trigger a "failed" status
- Unrecognized headers are allowed (stored in `extra_json`)

**Row Validation:**
- **Name:** Required, must not be empty
- **Thickness, Length, Width, SquareFeet, Cost, Price:** Must be valid numbers
- **Quantity:** Must be a valid integer
- Empty rows are skipped

**Errors are reported with:**
- Row number (1-indexed, row 1 is header)
- Column name
- Descriptive error message

---

### Upsert Logic

- **If `SlabID` column is present and matches an existing slab:** Updates that slab
- **If `SlabID` is missing or doesn't match:** Creates a new slab with auto-generated ID
- **Default values for new slabs:**
  - `status`: "available"
  - `quantity`: 1

---

## Export API (Phase 3)

### Export Slabs

**Endpoint:** `GET /api/v1/export/slabs`

Exports slab data in CSV or JSON format with optional filtering.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `format` | String | Export format: `csv` or `json` (default: `csv`) |
| `name` | String | Filter by slab name (case-insensitive partial match) |
| `stone_type` | String | Filter by stone type |
| `location` | String | Filter by storage location |
| `status` | String | Filter by status |
| `min_thickness` | Float | Minimum thickness filter |
| `max_thickness` | Float | Maximum thickness filter |
| `min_price` | Float | Minimum price filter |
| `max_price` | Float | Maximum price filter |

---

### CSV Export

**Request:**
```bash
GET /api/v1/export/slabs?format=csv
```

**Response:**
- **Content-Type:** `text/csv`
- **Headers:** `Content-Disposition: attachment; filename=slabs_export.csv`

**CSV Columns (19 total):**
1. SlabID (public_id)
2. Name
3. StoneType
4. Supplier
5. Finish
6. Thickness
7. Color
8. Length
9. Width
10. SquareFeet
11. Location
12. Status
13. Quantity
14. Cost
15. Price
16. Tags
17. Notes
18. CreatedAt
19. UpdatedAt

**Example:**
```bash
# Export all slabs as CSV
curl http://localhost:8000/api/v1/export/slabs?format=csv -o slabs.csv

# Export only available slabs with thickness >= 2.0
curl "http://localhost:8000/api/v1/export/slabs?format=csv&status=available&min_thickness=2.0" -o available_slabs.csv

# Export slabs by name filter
curl "http://localhost:8000/api/v1/export/slabs?format=csv&name=marble" -o marble_slabs.csv
```

---

### JSON Export

**Request:**
```bash
GET /api/v1/export/slabs?format=json
```

**Response:**
```json
{
  "total": 750,
  "filters": {
    "status": "available",
    "min_thickness": 2.0
  },
  "slabs": [
    {
      "id": 1,
      "public_id": "ABC123",
      "name": "Calacatta Marble",
      "stone_type": "Marble",
      "supplier": "Stone Supplier Inc",
      "finish": "Polished",
      "thickness": 2.0,
      "color": "White",
      "length": 120.0,
      "width": 60.0,
      "square_feet": 50.0,
      "location": "Warehouse A",
      "status": "available",
      "quantity": 1,
      "tags": "premium,italian",
      "notes": "Beautiful veining",
      "primary_image": "/storage/images/abc123.jpg",
      "cost": 500.0,
      "price": 750.0,
      "created_at": "2026-01-15T10:30:00",
      "updated_at": "2026-01-18T14:20:00",
      "import_source": "csv_metadata",
      "import_batch_id": "batch_12345"
    }
  ]
}
```

**Example:**
```bash
# Export as JSON
curl http://localhost:8000/api/v1/export/slabs?format=json

# Export with filters
curl "http://localhost:8000/api/v1/export/slabs?format=json&location=Warehouse%20A&min_price=500"
```

---

### Filter Combinations

You can combine multiple filters:

```bash
# Marble slabs in Warehouse A, thickness 2-3 inches, price $500-$1000
GET /api/v1/export/slabs?format=csv&stone_type=marble&location=Warehouse%20A&min_thickness=2.0&max_thickness=3.0&min_price=500&max_price=1000
```

**Filter Matching:**
- `name`, `stone_type`, `location`: Case-insensitive partial match (uses SQL `ILIKE`)
- `status`: Exact match
- Numeric ranges: Inclusive (e.g., `min_thickness=2.0` includes slabs with thickness exactly 2.0)

---

## Common Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 303 | See Other (redirect after form submission) |
| 400 | Bad Request (validation error) |
| 415 | Unsupported Media Type (wrong file format) |
| 500 | Internal Server Error |

---

## Error Responses

**Unsupported File Format:**
```json
{
  "error": "Unsupported file type: .txt. Use .csv or .xlsx"
}
```

**Unsupported Export Format:**
```json
{
  "error": "Unsupported export format",
  "supported_formats": ["csv", "json"]
}
```

**Import Validation Errors:**
```json
{
  "batch_id": "batch_123",
  "status": "failed",
  "errors": [
    {
      "row": 2,
      "column": "Name",
      "message": "Required field 'name' is empty"
    },
    {
      "row": 5,
      "column": "Thickness",
      "message": "Invalid number: 'abc'"
    }
  ]
}
```

---

## Future Features (Phases 4+)

The following features are planned but not yet fully documented:

- **Pagination & Sorting** - Query parameters for paginated slab lists
- **Job Queue API** - Async job management (`/api/v1/jobs`, `/api/v1/workers`)
- **Admin Settings API** - Maintenance mode, read-only mode (`/api/v1/admin/settings`)
- **GPT Analysis** - AI-powered slab analysis (`/api/v1/gpt`)
- **Reference Catalog** - Stone type catalog (`/api/v1/catalog`)

These will be documented as they are completed in upcoming phases.

---

## Additional Resources

- **Main Documentation:** [README.md](README.md)
- **Governance:** [PRE_PHASE0_BASELINE.md](PRE_PHASE0_BASELINE.md)
- **Phase Plan:** [PHASE_EXECUTION_PLAN.md](PHASE_EXECUTION_PLAN.md)
- **Interactive Docs:** http://localhost:8000/docs

For support or questions, refer to the project's GitHub issues or internal documentation.
