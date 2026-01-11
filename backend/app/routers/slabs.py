"""
Slab API routes for SlabHub
RESTful endpoints for slab inventory management
"""
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.models import get_db
from backend.app.schemas import (
    SlabCreate,
    SlabUpdate,
    SlabResponse,
    SlabListResponse,
    QRGenerateRequest,
    QRGenerateResponse,
    LabelGenerateResponse,
)
from backend.app import crud
from backend.app.config import settings
from backend.app.utils import generate_qr_code, generate_label_pdf

logger = logging.getLogger(__name__)

# Create router with no prefix (will be mounted at /api/v1/slabs)
router = APIRouter(tags=["slabs"])


# ============================================================================
# Slab CRUD Endpoints
# ============================================================================

@router.get("/", response_model=SlabListResponse)
def list_slabs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search in name, stone_type, supplier, etc."),
    stone_type: Optional[str] = Query(None, description="Filter by stone type"),
    supplier: Optional[str] = Query(None, description="Filter by supplier"),
    location: Optional[str] = Query(None, description="Filter by location"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    List all slabs with optional filtering and pagination.

    Supports:
    - Pagination via skip/limit
    - Full-text search across multiple fields
    - Filtering by stone_type, supplier, location, status
    """
    try:
        # Build filters dictionary
        filters = {}
        if search:
            filters["search"] = search
        if stone_type:
            filters["stone_type"] = stone_type
        if supplier:
            filters["supplier"] = supplier
        if location:
            filters["location"] = location
        if status:
            filters["status"] = status

        # Get slabs from database
        slabs, total = crud.get_slabs(db, skip=skip, limit=limit, filters=filters)

        return SlabListResponse(
            total=total,
            skip=skip,
            limit=limit,
            items=slabs
        )

    except Exception as e:
        logger.error(f"Error listing slabs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{slab_id}", response_model=SlabResponse)
def get_slab(slab_id: int, db: Session = Depends(get_db)):
    """
    Get a single slab by ID.

    Args:
        slab_id: Slab database ID

    Returns:
        Slab details

    Raises:
        404: Slab not found
    """
    try:
        slab = crud.get_slab(db, slab_id)
        if not slab:
            raise HTTPException(status_code=404, detail=f"Slab {slab_id} not found")

        return slab

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting slab {slab_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/public/{public_id}", response_model=SlabResponse)
def get_slab_by_public_id(public_id: str, db: Session = Depends(get_db)):
    """
    Get a single slab by public ID (used for QR codes).

    Args:
        public_id: Public identifier for the slab

    Returns:
        Slab details

    Raises:
        404: Slab not found
    """
    try:
        slab = crud.get_slab_by_public_id(db, public_id)
        if not slab:
            raise HTTPException(status_code=404, detail=f"Slab with public_id '{public_id}' not found")

        return slab

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting slab by public_id {public_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=SlabResponse, status_code=201)
def create_slab(slab_data: SlabCreate, db: Session = Depends(get_db)):
    """
    Create a new slab.

    Args:
        slab_data: Slab creation data

    Returns:
        Created slab details

    Raises:
        400: Invalid input data
        500: Server error
    """
    try:
        slab = crud.create_slab(db, slab_data)
        if not slab:
            raise HTTPException(status_code=400, detail="Failed to create slab")

        logger.info(f"Created new slab: {slab.public_id} (ID: {slab.id})")
        return slab

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating slab: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{slab_id}", response_model=SlabResponse)
def update_slab(slab_id: int, slab_data: SlabUpdate, db: Session = Depends(get_db)):
    """
    Update an existing slab.

    Args:
        slab_id: Slab ID to update
        slab_data: Slab update data (only provided fields will be updated)

    Returns:
        Updated slab details

    Raises:
        404: Slab not found
        500: Server error
    """
    try:
        slab = crud.update_slab(db, slab_id, slab_data)
        if not slab:
            raise HTTPException(status_code=404, detail=f"Slab {slab_id} not found")

        logger.info(f"Updated slab: {slab.public_id} (ID: {slab.id})")
        return slab

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating slab {slab_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{slab_id}", status_code=204)
def delete_slab(slab_id: int, db: Session = Depends(get_db)):
    """
    Delete a slab.

    Args:
        slab_id: Slab ID to delete

    Returns:
        No content (204)

    Raises:
        404: Slab not found
        500: Server error
    """
    try:
        success = crud.delete_slab(db, slab_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Slab {slab_id} not found")

        logger.info(f"Deleted slab ID: {slab_id}")
        return Response(status_code=204)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting slab {slab_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# QR Code Generation Endpoint
# ============================================================================

@router.post("/{slab_id}/generate-qr", response_model=QRGenerateResponse)
def generate_slab_qr_code(
    slab_id: int,
    request: QRGenerateRequest = QRGenerateRequest(),
    db: Session = Depends(get_db)
):
    """
    Generate a QR code for a slab.

    The QR code encodes the public URL for the slab (for kiosk display).

    Args:
        slab_id: Slab ID to generate QR code for
        request: QR generation options (regenerate flag)

    Returns:
        QR code generation result with path and URL

    Raises:
        404: Slab not found
        500: QR code generation failed
    """
    try:
        # Get slab
        slab = crud.get_slab(db, slab_id)
        if not slab:
            raise HTTPException(status_code=404, detail=f"Slab {slab_id} not found")

        # Check if QR code already exists
        if slab.qr_code_path and not request.regenerate:
            qr_path = Path(slab.qr_code_path)
            if qr_path.exists():
                logger.info(f"QR code already exists for slab {slab.public_id}")
                return QRGenerateResponse(
                    slab_id=slab.id,
                    public_id=slab.public_id,
                    qr_code_path=str(qr_path),
                    qr_url=f"{settings.public_base_url}/s/{slab.public_id}"
                )

        # Generate QR code
        try:
            qr_path = generate_qr_code(slab.public_id)
        except Exception as qr_error:
            logger.error(f"QR code generation failed: {qr_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"QR code generation failed: {str(qr_error)}")

        # Update slab with QR code path
        slab.qr_code_path = str(qr_path)
        db.commit()

        logger.info(f"Generated QR code for slab {slab.public_id}: {qr_path}")

        return QRGenerateResponse(
            slab_id=slab.id,
            public_id=slab.public_id,
            qr_code_path=str(qr_path),
            qr_url=f"{settings.public_base_url}/s/{slab.public_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating QR code for slab {slab_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Label Generation Endpoint
# ============================================================================

@router.get("/{slab_id}/label", response_class=FileResponse)
def generate_slab_label(slab_id: int, db: Session = Depends(get_db)):
    """
    Generate and download a PDF label for a slab.

    Creates a 4x6 inch thermal printer label with QR code and slab details.

    Args:
        slab_id: Slab ID to generate label for

    Returns:
        PDF file download

    Raises:
        404: Slab not found
        500: Label generation failed
    """
    try:
        # Get slab
        slab = crud.get_slab(db, slab_id)
        if not slab:
            raise HTTPException(status_code=404, detail=f"Slab {slab_id} not found")

        # Generate label PDF
        try:
            label_path = generate_label_pdf(slab)
        except Exception as label_error:
            logger.error(f"Label generation failed: {label_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Label generation failed: {str(label_error)}")

        # Verify file exists
        if not label_path.exists():
            raise HTTPException(status_code=500, detail="Label file not found after generation")

        logger.info(f"Generated label for slab {slab.public_id}: {label_path}")

        # Return PDF file for download
        return FileResponse(
            path=str(label_path),
            media_type="application/pdf",
            filename=f"{slab.public_id}_label.pdf",
            headers={
                "Content-Disposition": f"attachment; filename={slab.public_id}_label.pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating label for slab {slab_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
