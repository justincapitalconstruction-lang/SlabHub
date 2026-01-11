"""
Services module for SlabHub backend.

This package provides high-level business logic services for the application,
including watch folder monitoring and image import processing.
"""

from backend.app.services.watch_folder import (
    SlabCropEventHandler,
    WatchFolderService,
    get_watch_service,
)

from backend.app.services.import_processor import (
    ImportProcessor,
)

__all__ = [
    # Watch folder services
    "SlabCropEventHandler",
    "WatchFolderService",
    "get_watch_service",
    # Import processing
    "ImportProcessor",
]
