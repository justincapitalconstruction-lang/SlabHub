"""
Export router for SlabHub.

Provides API endpoints for exporting slab data in various formats (CSV, JSON).
"""
from fastapi import APIRouter, Query, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, List
from sqlalchemy.orm import Session
import csv
import io

from backend.app.models import Slab, get_db
from backend.app.schemas import SlabResponse

router = APIRouter()


def query_slabs(db: Session, filters: dict) -> List[Slab]:
    """
    Query slabs with optional filters.

    Args:
        db: Database session
        filters: Dictionary of filter criteria

    Returns:
        List of Slab objects matching filters
    """
    q = db.query(Slab)

    if filters.get("name"):
        q = q.filter(Slab.name.ilike(f"%{filters['name']}%"))

    if filters.get("stone_type"):
        q = q.filter(Slab.stone_type.ilike(f"%{filters['stone_type']}%"))

    if filters.get("location"):
        q = q.filter(Slab.location.ilike(f"%{filters['location']}%"))

    if filters.get("status"):
        q = q.filter(Slab.status == filters['status'])

    if filters.get("min_thickness") is not None:
        q = q.filter(Slab.thickness >= filters["min_thickness"])

    if filters.get("max_thickness") is not None:
        q = q.filter(Slab.thickness <= filters["max_thickness"])

    if filters.get("min_price") is not None:
        q = q.filter(Slab.price >= filters["min_price"])

    if filters.get("max_price") is not None:
        q = q.filter(Slab.price <= filters["max_price"])

    return q.all()


@router.get(
    "/api/v1/export/slabs",
    name="export_slabs",
    summary="Export slabs with filters",
    description="Export slab inventory to CSV or JSON format with optional filtering by name, type, location, status, dimensions, and price.",
    tags=["Export"],
    responses={
        200: {
            "description": "Successful export",
            "content": {
                "text/csv": {
                    "example": "SlabID,Name,StoneType,Supplier,Thickness,Location,...\nABC123,Calacatta Marble,Marble,Stone Inc,2.0,Warehouse A,..."
                },
                "application/json": {
                    "example": {
                        "total": 100,
                        "filters": {"status": "available"},
                        "slabs": [{"id": 1, "public_id": "ABC123", "name": "Calacatta Marble"}]
                    }
                }
            }
        },
        400: {"description": "Invalid filter parameters"}
    }
)
def export_slabs(
    name: Optional[str] = Query(None, description="Filter by slab name (case-insensitive partial match)", example="marble"),
    stone_type: Optional[str] = Query(None, description="Filter by stone type (e.g., Marble, Granite, Quartzite)", example="Marble"),
    location: Optional[str] = Query(None, description="Filter by storage location", example="Warehouse A"),
    status: Optional[str] = Query(None, description="Filter by status (available, reserved, sold, etc.)", example="available"),
    min_thickness: Optional[float] = Query(None, description="Minimum thickness in inches", ge=0, example=2.0),
    max_thickness: Optional[float] = Query(None, description="Maximum thickness in inches", ge=0, example=3.0),
    min_price: Optional[float] = Query(None, description="Minimum price in dollars", ge=0, example=500.0),
    max_price: Optional[float] = Query(None, description="Maximum price in dollars", ge=0, example=2000.0),
    format: str = Query("csv", description="Export format: 'csv' for CSV file download or 'json' for JSON response", regex="^(csv|json)$", example="csv"),
    db: Session = Depends(get_db)
):
    """
    Export slabs to CSV or JSON format with optional filtering.

    **CSV Export:**
    - Returns a downloadable CSV file with 19 columns
    - Includes all slab metadata (ID, name, dimensions, pricing, etc.)
    - Filename: `slabs_export.csv`

    **JSON Export:**
    - Returns structured JSON with total count, applied filters, and slab array
    - All fields include ISO timestamps for created_at/updated_at

    **Filtering:**
    - Multiple filters can be combined (AND logic)
    - Text filters (name, stone_type, location) use case-insensitive partial matching
    - Numeric filters (thickness, price) use inclusive ranges
    - Status filter uses exact matching

    **Example Requests:**
    - Export all as CSV: `GET /api/v1/export/slabs?format=csv`
    - Available slabs only: `GET /api/v1/export/slabs?format=json&status=available`
    - Price range filter: `GET /api/v1/export/slabs?format=csv&min_price=500&max_price=2000`
    - Combined filters: `GET /api/v1/export/slabs?format=json&stone_type=marble&location=Warehouse%20A`
    """
    filters = {
        "name": name,
        "stone_type": stone_type,
        "location": location,
        "status": status,
        "min_thickness": min_thickness,
        "max_thickness": max_thickness,
        "min_price": min_price,
        "max_price": max_price
    }

    slabs = query_slabs(db, filters)

    if format == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream)

        # CSV Header
        writer.writerow([
            "SlabID",
            "Name",
            "StoneType",
            "Supplier",
            "Finish",
            "Thickness",
            "Color",
            "Length",
            "Width",
            "SquareFeet",
            "Location",
            "Status",
            "Quantity",
            "Cost",
            "Price",
            "Tags",
            "Notes",
            "CreatedAt",
            "UpdatedAt"
        ])

        # CSV Data
        for slab in slabs:
            writer.writerow([
                slab.public_id,
                slab.name,
                slab.stone_type or "",
                slab.supplier or "",
                slab.finish or "",
                slab.thickness or "",
                slab.color or "",
                slab.length or "",
                slab.width or "",
                slab.square_feet or "",
                slab.location or "",
                slab.status or "",
                slab.quantity or "",
                slab.cost or "",
                slab.price or "",
                slab.tags or "",
                slab.notes or "",
                slab.created_at.isoformat() if slab.created_at else "",
                slab.updated_at.isoformat() if slab.updated_at else ""
            ])

        stream.seek(0)

        return StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=slabs_export.csv"
            }
        )

    elif format == "json":
        # Convert to JSON-serializable dicts
        return {
            "total": len(slabs),
            "filters": {k: v for k, v in filters.items() if v is not None},
            "slabs": [
                {
                    "id": slab.id,
                    "public_id": slab.public_id,
                    "name": slab.name,
                    "stone_type": slab.stone_type,
                    "supplier": slab.supplier,
                    "finish": slab.finish,
                    "thickness": slab.thickness,
                    "color": slab.color,
                    "length": slab.length,
                    "width": slab.width,
                    "square_feet": slab.square_feet,
                    "location": slab.location,
                    "status": slab.status,
                    "quantity": slab.quantity,
                    "tags": slab.tags,
                    "notes": slab.notes,
                    "primary_image": slab.primary_image,
                    "cost": slab.cost,
                    "price": slab.price,
                    "created_at": slab.created_at.isoformat() if slab.created_at else None,
                    "updated_at": slab.updated_at.isoformat() if slab.updated_at else None,
                    "import_source": slab.import_source,
                    "import_batch_id": slab.import_batch_id
                }
                for slab in slabs
            ]
        }

    else:
        return {
            "error": "Unsupported export format",
            "supported_formats": ["csv", "json"]
        }
