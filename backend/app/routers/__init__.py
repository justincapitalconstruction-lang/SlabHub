"""
SlabHub API Routers
Exports all routers for the application
"""
from backend.app.routers import (
    slabs,
    admin,
    kiosk,
    jobs,
    workers,
    gpt,
    catalog,
    admin_settings,
)

__all__ = [
    "slabs",
    "admin",
    "kiosk",
    "jobs",
    "workers",
    "gpt",
    "catalog",
    "admin_settings",
]
