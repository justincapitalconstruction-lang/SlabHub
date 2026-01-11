"""
Kiosk router for SlabHub
Public-facing browse and search interface for customers
Mobile-responsive with large touch targets
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from backend.app.models import get_db
from backend.app.crud import get_slabs, get_slab_by_public_id, search_slabs
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

# Templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


# ============================================================================
# Kiosk Browse
# ============================================================================

@router.get("/kiosk", response_class=HTMLResponse, name="kiosk_browse")
async def kiosk_browse(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    stone_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Public kiosk browse interface.

    Features:
    - Large tile cards for slabs
    - Search functionality
    - Filters for stone type and status
    - Mobile-optimized layout
    - Touch-friendly buttons
    """
    try:
        # Pagination
        limit = 12  # Show 12 slabs per page (3x4 grid on desktop)
        skip = (page - 1) * limit

        # Build filters - only show available slabs by default
        filters = {"status": status or "available"}
        if search:
            filters["search"] = search
        if stone_type:
            filters["stone_type"] = stone_type

        # Get slabs
        slabs, total = get_slabs(db, skip=skip, limit=limit, filters=filters)

        # Calculate pagination
        total_pages = (total + limit - 1) // limit

        # Get unique stone types for filter
        from backend.app.models import Slab
        stone_types = db.query(Slab.stone_type).distinct().filter(
            Slab.stone_type.isnot(None),
            Slab.status == "available"
        ).all()
        stone_types = sorted([st[0] for st in stone_types])

        return templates.TemplateResponse("kiosk/browse.html", {
            "request": request,
            "slabs": slabs,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "search": search or "",
            "stone_type": stone_type or "",
            "stone_types": stone_types,
        })

    except Exception as e:
        logger.error(f"Error loading kiosk browse: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load browse page")


# ============================================================================
# Slab Detail (Public View)
# ============================================================================

@router.get("/kiosk/slab/{public_id}", response_class=HTMLResponse, name="kiosk_slab_view")
async def kiosk_slab_view(
    request: Request,
    public_id: str,
    db: Session = Depends(get_db)
):
    """
    Public slab detail view.

    Features:
    - Large image display
    - Clean layout with essential details
    - Mobile-responsive
    - Easy-to-read typography
    - Contact/inquiry button
    """
    try:
        slab = get_slab_by_public_id(db, public_id)
        if not slab:
            raise HTTPException(status_code=404, detail="Slab not found")

        return templates.TemplateResponse("kiosk/slab_view.html", {
            "request": request,
            "slab": slab,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading slab view: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load slab")


# ============================================================================
# Search API (JSON endpoint for AJAX)
# ============================================================================

@router.get("/kiosk/search", response_class=JSONResponse, name="kiosk_search_api")
async def kiosk_search_api(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: Session = Depends(get_db)
):
    """
    JSON search API for autocomplete and dynamic search.

    Args:
        q: Search query string (minimum 2 characters)
        limit: Maximum number of results (default: 10, max: 50)

    Returns:
        JSON array of matching slabs with basic info
    """
    try:
        # Search slabs (only available ones for public kiosk)
        slabs = search_slabs(db, q, limit=limit)

        # Filter to only available slabs
        slabs = [s for s in slabs if s.status == "available"]

        # Return simplified data
        results = [
            {
                "id": slab.id,
                "public_id": slab.public_id,
                "name": slab.name,
                "stone_type": slab.stone_type,
                "color": slab.color,
                "location": slab.location,
                "square_feet": slab.square_feet,
                "price": slab.price,
                "primary_image": slab.primary_image,
                "url": f"/kiosk/slab/{slab.public_id}"
            }
            for slab in slabs[:limit]
        ]

        return JSONResponse(content={
            "query": q,
            "count": len(results),
            "results": results
        })

    except Exception as e:
        logger.error(f"Error in search API: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed")


# ============================================================================
# Featured Slabs (optional enhancement)
# ============================================================================

@router.get("/kiosk/featured", response_class=JSONResponse, name="kiosk_featured")
async def kiosk_featured(
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """
    Get featured slabs for homepage carousel or highlights.

    Returns most recent available slabs with images.
    """
    try:
        from backend.app.models import Slab

        # Get recent available slabs with images
        slabs = db.query(Slab).filter(
            Slab.status == "available",
            Slab.primary_image.isnot(None)
        ).order_by(Slab.created_at.desc()).limit(limit).all()

        results = [
            {
                "id": slab.id,
                "public_id": slab.public_id,
                "name": slab.name,
                "stone_type": slab.stone_type,
                "color": slab.color,
                "square_feet": slab.square_feet,
                "price": slab.price,
                "primary_image": slab.primary_image,
                "url": f"/kiosk/slab/{slab.public_id}"
            }
            for slab in slabs
        ]

        return JSONResponse(content={
            "count": len(results),
            "slabs": results
        })

    except Exception as e:
        logger.error(f"Error getting featured slabs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get featured slabs")
