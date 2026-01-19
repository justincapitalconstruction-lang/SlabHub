"""
Admin router for SlabHub
Server-side rendered admin interface with Bootstrap 5
"""
import logging
import shutil
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form, Depends, HTTPException, status, UploadFile, File
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
from backend.app.schemas import SlabCreate, SlabUpdate, BulkActionRequest
from backend.app.services.import_processor import ImportProcessor
from backend.app.utils.qr_generator import generate_qr_code
from backend.app.utils.label_printer import generate_label_pdf as generate_label
from pathlib import Path
from backend.app.config import settings

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


async def _save_slab_image(slab, file) -> Optional[str]:
    """
    Helper to save an uploaded image for a slab and return the path.
    """
    if not file or not file.filename:
        return None
        
    # Create archive directory
    archive_base = Path(settings.processed_archive_folder)
    date_str = datetime.now().strftime("%Y%m%d")
    upload_dir = archive_base / "manual" / date_str
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Build destination path
    file_ext = Path(file.filename).suffix
    dest_filename = f"{slab.public_id}_{datetime.now().strftime('%H%M%S')}{file_ext}"
    dest_path = upload_dir / dest_filename

    # Save file
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return str(dest_path)


@router.post("/admin/slabs/{slab_id}/upload-image", response_class=HTMLResponse, name="admin_slab_upload_image")
async def admin_slab_upload_image(
    slab_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a new primary image for a slab.
    """
    try:
        slab = get_slab(db, slab_id)
        if not slab:
            raise HTTPException(status_code=404, detail="Slab not found")

        image_path = await _save_slab_image(slab, file)
        if image_path:
            # Calculate perceptual hash
            from backend.app.utils import calculate_perceptual_hash
            phash = calculate_perceptual_hash(Path(image_path))

            # Update slab
            slab.primary_image = image_path
            if phash:
                slab.perceptual_hash = phash
            
            db.commit()
            logger.info(f"Uploaded new image for slab {slab.public_id}: {image_path}")

        return RedirectResponse(
            url=f"/admin/slabs/{slab_id}?success=image_uploaded",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        logger.error(f"Error uploading image for slab {slab_id}: {e}", exc_info=True)
        return RedirectResponse(
            url=f"/admin/slabs/{slab_id}?error=Failed+to+upload+image",
            status_code=status.HTTP_303_SEE_OTHER
        )


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
    image_file: Optional[UploadFile] = File(None),
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

        # Handle image upload if provided
        if image_file and image_file.filename:
            image_path = await _save_slab_image(new_slab, image_file)
            if image_path:
                from backend.app.utils import calculate_perceptual_hash
                phash = calculate_perceptual_hash(Path(image_path))
                
                new_slab.primary_image = image_path
                if phash:
                    new_slab.perceptual_hash = phash
                db.commit()
                logger.info(f"Uploaded image during creation for slab {new_slab.public_id}: {image_path}")

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


@router.post("/admin/import/upload", name="admin_import_upload")
async def admin_import_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Import slab metadata from an uploaded CSV or XLSX file.

    Supports:
    - .csv files (UTF-8 or Latin-1 encoded)
    - .xlsx files (requires openpyxl)

    Returns redirect to imports list with status message.
    """
    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: .{ext}. Use .csv or .xlsx"
        )

    try:
        content = await file.read()

        processor = ImportProcessor(db)
        results = processor.process_file_upload(content, filename)

        # Build redirect URL based on results
        if results["status"] == "completed":
            msg = f"success=Imported {results['rows_imported']} slabs, updated {results['rows_updated']}"
        elif results["status"] == "partial":
            msg = f"warning=Partial import: {results['rows_imported']} imported, {results['rows_updated']} updated, {results['rows_failed']} failed"
        else:
            msg = f"error={results['summary']}"

        return RedirectResponse(
            url=f"/admin/imports?{msg}",
            status_code=status.HTTP_303_SEE_OTHER
        )

    except Exception as e:
        logger.error(f"Error during file upload: {e}", exc_info=True)
        return RedirectResponse(
            url=f"/admin/imports?error={str(e)}",
            status_code=status.HTTP_303_SEE_OTHER
        )


@router.post("/api/v1/import/metadata", name="api_import_metadata")
async def api_import_metadata(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    API endpoint for metadata import (returns JSON).

    Supports:
    - .csv files (UTF-8 or Latin-1 encoded)
    - .xlsx files (requires openpyxl)

    Returns:
        ImportResult with batch_id, status, row counts, and errors
    """
    from backend.app.schemas import ImportResult, ImportRowError

    filename = file.filename or ""
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: .{ext}. Use .csv or .xlsx"
        )

    try:
        content = await file.read()

        processor = ImportProcessor(db)
        results = processor.process_file_upload(content, filename)

        # Convert to Pydantic model
        return ImportResult(
            batch_id=results["batch_id"],
            status=results["status"],
            file_type=results["file_type"],
            rows_processed=results["rows_processed"],
            rows_imported=results["rows_imported"],
            rows_updated=results["rows_updated"],
            rows_failed=results["rows_failed"],
            rows_skipped=results["rows_skipped"],
            errors=[ImportRowError(**e) for e in results["errors"]],
            warnings=[ImportRowError(**w) for w in results["warnings"]],
            summary=results["summary"]
        )

    except Exception as e:
        logger.error(f"Error during API import: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/admin/import/metadata", name="admin_import_metadata")
async def admin_import_metadata(
    db: Session = Depends(get_db)
):
    """
    Trigger metadata import from configured file path.
    """
    try:
        processor = ImportProcessor(db)
        success = processor.process_metadata_file()
        processor.finalize()

        if success:
            return RedirectResponse(
                url="/admin/imports?success=import_completed",
                status_code=status.HTTP_303_SEE_OTHER
            )
        else:
            return RedirectResponse(
                url="/admin/imports?error=import_failed",
                status_code=status.HTTP_303_SEE_OTHER
            )

    except Exception as e:
        logger.error(f"Error triggering import: {e}", exc_info=True)
        return RedirectResponse(
            url=f"/admin/imports?error={str(e)}",
            status_code=status.HTTP_303_SEE_OTHER
        )


@router.post("/api/v1/admin/slabs/bulk", name="admin_slabs_bulk_action")
async def admin_slabs_bulk_action(
    request: BulkActionRequest,
    db: Session = Depends(get_db)
):
    """
    Perform bulk actions on multiple slabs.
    """
    try:
        logger.info(f"Bulk action requested: {request.action} on {len(request.ids)} slabs")
        
        if request.action == "delete":
            # Bulk delete
            count = db.query(Slab).filter(Slab.id.in_(request.ids)).delete(synchronize_session=False)
            db.commit()
            return {"count": count, "action": "delete"}
            
        elif request.action == "update_status":
            if not request.status:
                raise HTTPException(status_code=400, detail="Status is required for update_status action")
            
            count = db.query(Slab).filter(Slab.id.in_(request.ids)).update(
                {Slab.status: request.status}, 
                synchronize_session=False
            )
            db.commit()
            return {"count": count, "action": "update_status"}
            
        elif request.action == "update_location":
            if not request.location:
                raise HTTPException(status_code=400, detail="Location is required for update_location action")
            
            count = db.query(Slab).filter(Slab.id.in_(request.ids)).update(
                {Slab.location: request.location}, 
                synchronize_session=False
            )
            db.commit()
            return {"count": count, "action": "update_location"}
            
        elif request.action == "analyze":
            # For now, we'll just log this as a placeholder for Phase 4
            # In Phase 4, this would trigger background jobs for GPT analysis
            logger.warning(f"Bulk analysis not yet fully implemented (Phase 4 scope). Requested for {len(request.ids)} slabs.")
            return {"count": len(request.ids), "action": "analyze", "message": "Bulk analysis queued (placeholder)"}
            
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported bulk action: {request.action}")

    except Exception as e:
        logger.error(f"Error during bulk action: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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
