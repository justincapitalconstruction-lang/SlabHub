"""
Admin router for SlabHub
Server-side rendered admin interface with Bootstrap 5
"""
import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models import Slab, ImportLog, get_db
from backend.app.crud import (
    get_slabs,
    get_slab,
    create_slab,
    update_slab,
    delete_slab,
)
from backend.app.schemas import SlabCreate, SlabUpdate
from backend.app.services.import_processor import ImportProcessor
from backend.app.utils.qr_generator import generate_qr_code
from backend.app.utils.label_printer import generate_label
from pathlib import Path

logger = logging.getLogger(__name__)

router = APIRouter()

# Templates
templates_path = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))


# ============================================================================
# Dashboard
# ============================================================================

@router.get("/admin", response_class=HTMLResponse, name="admin_dashboard")
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Admin dashboard with statistics and recent activity.

    Displays:
    - Total slabs count
    - Available slabs count
    - Sold slabs count
    - Recent imports count
    - Recent slabs (last 10)
    """
    try:
        # Get statistics
        total_slabs = db.query(func.count(Slab.id)).scalar() or 0
        available_slabs = db.query(func.count(Slab.id)).filter(Slab.status == "available").scalar() or 0
        sold_slabs = db.query(func.count(Slab.id)).filter(Slab.status == "sold").scalar() or 0

        # Recent imports (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_imports = db.query(func.count(ImportLog.id)).filter(
            ImportLog.created_at >= week_ago
        ).scalar() or 0

        # Recent slabs (last 10)
        recent_slabs = db.query(Slab).order_by(Slab.created_at.desc()).limit(10).all()

        # Get unique stone types for filter
        stone_types = db.query(Slab.stone_type).distinct().filter(Slab.stone_type.isnot(None)).all()
        stone_types = [st[0] for st in stone_types]

        # Get unique locations for filter
        locations = db.query(Slab.location).distinct().filter(Slab.location.isnot(None)).all()
        locations = [loc[0] for loc in locations]

        return templates.TemplateResponse("admin/dashboard.html", {
            "request": request,
            "total_slabs": total_slabs,
            "available_slabs": available_slabs,
            "sold_slabs": sold_slabs,
            "recent_imports": recent_imports,
            "recent_slabs": recent_slabs,
            "stone_types": stone_types,
            "locations": locations,
        })

    except Exception as e:
        logger.error(f"Error loading admin dashboard: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load dashboard")


# ============================================================================
# Slabs List
# ============================================================================

@router.get("/admin/slabs", response_class=HTMLResponse, name="admin_slabs_list")
async def admin_slabs_list(
    request: Request,
    page: int = 1,
    search: Optional[str] = None,
    stone_type: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Admin slabs list with search, filters, and pagination.
    """
    try:
        # Pagination
        limit = 20
        skip = (page - 1) * limit

        # Build filters
        filters = {}
        if search:
            filters["search"] = search
        if stone_type:
            filters["stone_type"] = stone_type
        if status:
            filters["status"] = status
        if location:
            filters["location"] = location

        # Get slabs
        slabs, total = get_slabs(db, skip=skip, limit=limit, filters=filters)

        # Calculate pagination
        total_pages = (total + limit - 1) // limit

        # Get unique values for filters
        stone_types = db.query(Slab.stone_type).distinct().filter(Slab.stone_type.isnot(None)).all()
        stone_types = [st[0] for st in stone_types]

        locations = db.query(Slab.location).distinct().filter(Slab.location.isnot(None)).all()
        locations = [loc[0] for loc in locations]

        statuses = ["available", "reserved", "sold", "damaged"]

        return templates.TemplateResponse("admin/slabs_list.html", {
            "request": request,
            "slabs": slabs,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "search": search or "",
            "stone_type": stone_type or "",
            "status": status or "",
            "location": location or "",
            "stone_types": stone_types,
            "locations": locations,
            "statuses": statuses,
        })

    except Exception as e:
        logger.error(f"Error loading slabs list: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load slabs list")


# ============================================================================
# Slab Detail/Edit
# ============================================================================

@router.get("/admin/slabs/{slab_id}", response_class=HTMLResponse, name="admin_slab_detail")
async def admin_slab_detail(
    request: Request,
    slab_id: int,
    db: Session = Depends(get_db)
):
    """
    Admin slab detail and edit form.
    """
    try:
        slab = get_slab(db, slab_id)
        if not slab:
            raise HTTPException(status_code=404, detail="Slab not found")

        # Get unique values for dropdowns
        stone_types = db.query(Slab.stone_type).distinct().filter(Slab.stone_type.isnot(None)).all()
        stone_types = [st[0] for st in stone_types]

        suppliers = db.query(Slab.supplier).distinct().filter(Slab.supplier.isnot(None)).all()
        suppliers = [s[0] for s in suppliers]

        locations = db.query(Slab.location).distinct().filter(Slab.location.isnot(None)).all()
        locations = [loc[0] for loc in locations]

        finishes = ["polished", "honed", "leathered", "brushed", "flamed"]
        statuses = ["available", "reserved", "sold", "damaged"]

        return templates.TemplateResponse("admin/slab_detail.html", {
            "request": request,
            "slab": slab,
            "stone_types": stone_types,
            "suppliers": suppliers,
            "locations": locations,
            "finishes": finishes,
            "statuses": statuses,
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading slab detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load slab detail")


@router.post("/admin/slabs/{slab_id}", response_class=HTMLResponse, name="admin_slab_update")
async def admin_slab_update(
    request: Request,
    slab_id: int,
    name: str = Form(...),
    stone_type: Optional[str] = Form(None),
    supplier: Optional[str] = Form(None),
    finish: Optional[str] = Form(None),
    thickness: Optional[float] = Form(None),
    color: Optional[str] = Form(None),
    length: Optional[float] = Form(None),
    width: Optional[float] = Form(None),
    square_feet: Optional[float] = Form(None),
    location: Optional[str] = Form(None),
    status: str = Form("available"),
    quantity: int = Form(1),
    tags: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    cost: Optional[float] = Form(None),
    price: Optional[float] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Update slab from form submission.
    """
    try:
        # Create update schema
        update_data = SlabUpdate(
            name=name,
            stone_type=stone_type or None,
            supplier=supplier or None,
            finish=finish or None,
            thickness=thickness,
            color=color or None,
            length=length,
            width=width,
            square_feet=square_feet,
            location=location or None,
            status=status,
            quantity=quantity,
            tags=tags or None,
            notes=notes or None,
            cost=cost,
            price=price,
        )

        # Update slab
        updated_slab = update_slab(db, slab_id, update_data)
        if not updated_slab:
            raise HTTPException(status_code=404, detail="Slab not found")

        # Redirect back to slab detail with success message
        return RedirectResponse(
            url=f"/admin/slabs/{slab_id}?success=updated",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating slab: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update slab")


# ============================================================================
# New Slab
# ============================================================================

@router.get("/admin/slabs/new", response_class=HTMLResponse, name="admin_slab_new")
async def admin_slab_new(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    New slab form.
    """
    try:
        # Get unique values for dropdowns
        stone_types = db.query(Slab.stone_type).distinct().filter(Slab.stone_type.isnot(None)).all()
        stone_types = [st[0] for st in stone_types]

        suppliers = db.query(Slab.supplier).distinct().filter(Slab.supplier.isnot(None)).all()
        suppliers = [s[0] for s in suppliers]

        locations = db.query(Slab.location).distinct().filter(Slab.location.isnot(None)).all()
        locations = [loc[0] for loc in locations]

        finishes = ["polished", "honed", "leathered", "brushed", "flamed"]
        statuses = ["available", "reserved", "sold", "damaged"]

        return templates.TemplateResponse("admin/slab_new.html", {
            "request": request,
            "stone_types": stone_types,
            "suppliers": suppliers,
            "locations": locations,
            "finishes": finishes,
            "statuses": statuses,
        })

    except Exception as e:
        logger.error(f"Error loading new slab form: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load new slab form")


@router.post("/admin/slabs", response_class=HTMLResponse, name="admin_slab_create")
async def admin_slab_create(
    request: Request,
    name: str = Form(...),
    stone_type: Optional[str] = Form(None),
    supplier: Optional[str] = Form(None),
    finish: Optional[str] = Form(None),
    thickness: Optional[float] = Form(None),
    color: Optional[str] = Form(None),
    length: Optional[float] = Form(None),
    width: Optional[float] = Form(None),
    square_feet: Optional[float] = Form(None),
    location: Optional[str] = Form(None),
    status: str = Form("available"),
    quantity: int = Form(1),
    tags: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    cost: Optional[float] = Form(None),
    price: Optional[float] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Create new slab from form submission.
    """
    try:
        # Create slab schema
        slab_data = SlabCreate(
            name=name,
            stone_type=stone_type or None,
            supplier=supplier or None,
            finish=finish or None,
            thickness=thickness,
            color=color or None,
            length=length,
            width=width,
            square_feet=square_feet,
            location=location or None,
            status=status,
            quantity=quantity,
            tags=tags or None,
            notes=notes or None,
            cost=cost,
            price=price,
        )

        # Create slab
        new_slab = create_slab(db, slab_data)
        if not new_slab:
            raise HTTPException(status_code=500, detail="Failed to create slab")

        # Redirect to slab detail with success message
        return RedirectResponse(
            url=f"/admin/slabs/{new_slab.id}?success=created",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating slab: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create slab")


# ============================================================================
# Delete Slab
# ============================================================================

@router.post("/admin/slabs/{slab_id}/delete", response_class=HTMLResponse, name="admin_slab_delete")
async def admin_slab_delete(
    slab_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete slab.
    """
    try:
        success = delete_slab(db, slab_id)
        if not success:
            raise HTTPException(status_code=404, detail="Slab not found")

        # Redirect to slabs list with success message
        return RedirectResponse(
            url="/admin/slabs?success=deleted",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting slab: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete slab")


# ============================================================================
# Import Management
# ============================================================================

@router.get("/admin/imports", response_class=HTMLResponse, name="admin_imports")
async def admin_imports(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Import history and management.
    """
    try:
        # Get recent imports
        imports = db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(50).all()

        return templates.TemplateResponse("admin/imports.html", {
            "request": request,
            "imports": imports,
        })

    except Exception as e:
        logger.error(f"Error loading imports: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load imports")


@router.post("/admin/import/metadata", name="admin_import_metadata")
async def admin_import_metadata(
    db: Session = Depends(get_db)
):
    """
    Trigger metadata import from configured file.
    """
    try:
        processor = ImportProcessor(db)
        success = processor.process_metadata_file()
        processor.finalize()

        if success:
            return RedirectResponse(
                url="/admin/imports?success=import_started",
                status_code=status.HTTP_303_SEE_OTHER
            )
        else:
            raise HTTPException(status_code=500, detail="Import failed")

    except Exception as e:
        logger.error(f"Error triggering import: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start import")


# ============================================================================
# QR Code and Label Generation
# ============================================================================

@router.post("/admin/slabs/{slab_id}/generate-qr", name="admin_generate_qr")
async def admin_generate_qr(
    slab_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate QR code for slab.
    """
    try:
        slab = get_slab(db, slab_id)
        if not slab:
            raise HTTPException(status_code=404, detail="Slab not found")

        # Generate QR code
        qr_path = generate_qr_code(slab.public_id)

        # Update slab with QR code path
        update_data = SlabUpdate(qr_code_path=str(qr_path))
        update_slab(db, slab_id, update_data)

        return RedirectResponse(
            url=f"/admin/slabs/{slab_id}?success=qr_generated",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating QR code: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate QR code")


@router.post("/admin/slabs/{slab_id}/generate-label", name="admin_generate_label")
async def admin_generate_label(
    slab_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate label for slab.
    """
    try:
        slab = get_slab(db, slab_id)
        if not slab:
            raise HTTPException(status_code=404, detail="Slab not found")

        # Generate label
        label_path = generate_label(slab)

        return RedirectResponse(
            url=f"/admin/slabs/{slab_id}?success=label_generated",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating label: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate label")
