"""API routes for managing operational modes (maintenance/read-only)."""
from fastapi import APIRouter, Depends

from backend.app.config import settings
from backend.app.security import require_admin

router = APIRouter()


@router.get("", summary="Get current operational mode flags")
def get_operational_modes():
    """Return the current maintenance and read-only flags."""
    return {
        "maintenance_mode": settings.maintenance_mode,
        "read_only_mode": settings.read_only_mode,
    }


@router.post("/maintenance", summary="Set maintenance mode")
def set_maintenance_mode(enabled: bool, _: str = Depends(require_admin)):
    """Toggle maintenance mode. Only accessible to admin."""
    settings.maintenance_mode = enabled
    return {"maintenance_mode": settings.maintenance_mode}


@router.post("/read-only", summary="Set read-only mode")
def set_read_only_mode(enabled: bool, _: str = Depends(require_admin)):
    """Toggle read-only mode. Only accessible to admin."""
    settings.read_only_mode = enabled
    return {"read_only_mode": settings.read_only_mode}
