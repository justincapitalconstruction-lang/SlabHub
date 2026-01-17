"""
SlabHub - Stone Slab Inventory Management System
Main FastAPI application with routes, services, and lifecycle management
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.app.config import settings
from backend.app.version import __version__
from backend.app.core.paths import log_path_map
import os
import shutil
from backend.app.models import init_db, SessionLocal, get_db
from backend.app.services.watch_folder import WatchFolderService
from backend.app.services.import_processor import ImportProcessor

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.log_file) if settings.log_file else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global watch folder service instance
watch_service: Optional[WatchFolderService] = None


# ============================================================================
# Lifespan Context Manager (Startup/Shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Startup:
    - Initialize database
    - Start watch folder service if enabled

    Shutdown:
    - Stop watch folder service gracefully
    """
    global watch_service

    # ========== STARTUP ==========
    logger.info("=" * 60)
    logger.info("SlabHub Application Starting...")
    logger.info("=" * 60)

    # Print version and root information early
    logger.info(f"Version: {__version__}")
    logger.info(f"Configured root: {settings.slabhub_root}")

    # Root path enforcement
    expected_root = Path(settings.slabhub_root).resolve()
    current_root = Path.cwd().resolve()
    if current_root != expected_root:
        logger.error(
            f"Invalid root directory. Expected {expected_root}, but running from {current_root}"
        )
        raise RuntimeError("SlabHub must be run from the configured root directory")

    # Initialize database
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise

    # Create required directories
    try:
        logger.info("Creating required directories...")
        dirs_to_create = [
            Path(settings.slabcrop_output_folder),
            Path(settings.slabcrop_inbox_folder),
            Path(settings.incoming_raw_folder),
            Path(settings.processed_archive_folder),
            Path(settings.label_output_folder),
            Path(settings.qr_output_folder),
            Path(settings.log_file).parent if settings.log_file else None,
        ]

        for dir_path in dirs_to_create:
            if dir_path:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {dir_path}")

        # Verify that all required directories exist after creation
        missing_dirs = [str(d) for d in dirs_to_create if d and not d.exists()]
        if missing_dirs:
            logger.error(f"Required directories missing: {missing_dirs}")
            raise RuntimeError(f"Required directories missing: {missing_dirs}")

        logger.info("Required directories created and verified successfully")
    except Exception as e:
        logger.error(f"Failed to create required directories: {e}", exc_info=True)
        # Non-fatal, continue startup

    # Start watch folder service if enabled
    if settings.enable_watch_folder:
        try:
            logger.info("Starting watch folder service...")

            # Create callback function for watch folder
            def watch_folder_callback(image_path: Path) -> None:
                """
                Callback function for watch folder service.
                Processes images using ImportProcessor.
                """
                try:
                    logger.info(f"Watch folder callback triggered for: {image_path.name}")

                    # Create database session for processing
                    db = SessionLocal()
                    try:
                        # Create import processor
                        processor = ImportProcessor(db)

                        # Process the image
                        success = processor.process_image(image_path)

                        if success:
                            logger.info(f"Successfully processed image: {image_path.name}")
                        else:
                            logger.warning(f"Failed to process image: {image_path.name}")

                        # Finalize processor (updates import log)
                        processor.finalize()

                    finally:
                        db.close()

                except Exception as e:
                    logger.error(f"Error in watch folder callback: {e}", exc_info=True)

            # Create and start watch service
            watch_path = Path(settings.slabcrop_output_folder)
            watch_service = WatchFolderService(watch_path, watch_folder_callback)
            watch_service.start()

            logger.info(f"Watch folder service started for: {watch_path}")

        except Exception as e:
            logger.error(f"Failed to start watch folder service: {e}", exc_info=True)
            # Non-fatal, continue startup
    else:
        logger.info("Watch folder service is disabled")

    logger.info("=" * 60)
    logger.info("SlabHub Application Started Successfully")
    logger.info(f"Public URL: {settings.public_base_url}")
    logger.info(f"Database: {settings.database_url}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info(f"Root Directory: {settings.slabhub_root}")
    # Log the mapping of logical directories to absolute paths
    log_path_map(logger)
    logger.info("=" * 60)

    # Yield control to application
    yield

    # ========== SHUTDOWN ==========
    logger.info("=" * 60)
    logger.info("SlabHub Application Shutting Down...")
    logger.info("=" * 60)

    # Stop watch folder service
    if watch_service and watch_service.is_running():
        try:
            logger.info("Stopping watch folder service...")
            watch_service.stop()
            logger.info("Watch folder service stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping watch folder service: {e}", exc_info=True)

    logger.info("=" * 60)
    logger.info("SlabHub Application Shutdown Complete")
    logger.info("=" * 60)


# ============================================================================
# Create FastAPI Application
# ============================================================================

app = FastAPI(
    title="SlabHub",
    description="Stone Slab Inventory Management System with SlabCrop Integration",
    version=__version__,
    lifespan=lifespan,
    debug=settings.debug,
)


# ============================================================================
# CORS Middleware
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)


# ============================================================================
# Static Files and Templates
# ============================================================================

# Static files directory
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)

try:
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    logger.info(f"Mounted static files at /static: {static_path}")
except Exception as e:
    logger.warning(f"Failed to mount static files: {e}")

# Templates directory
templates_path = Path(__file__).parent / "templates"
templates_path.mkdir(exist_ok=True)

templates = Jinja2Templates(directory=str(templates_path))
logger.info(f"Initialized templates from: {templates_path}")


# ============================================================================
# Include Routers
# ============================================================================

# Import routers
from backend.app.routers import slabs, admin, kiosk, jobs

# Mount API routers
app.include_router(
    slabs.router,
    prefix="/api/v1/slabs",
    tags=["slabs"]
)

# Mount Admin routers (server-side rendered)
app.include_router(
    admin.router,
    tags=["admin"]
)

# Mount Kiosk routers (public-facing)
app.include_router(
    kiosk.router,
    tags=["kiosk"]
)

# Mount Jobs API routers
app.include_router(
    jobs.router,
    prefix="/api/v1/jobs",
    tags=["jobs"]
)

logger.info("Registered routes:")
logger.info("  - /api/v1/slabs (Slab API)")
logger.info("  - /admin (Admin interface)")
logger.info("  - /kiosk (Public kiosk)")
logger.info("  - /api/v1/jobs (Job API)")


# ============================================================================
# Root and Health Check Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """
    Root endpoint - redirects to kiosk.

    Returns:
        Redirect to /kiosk
    """
    return RedirectResponse(url="/kiosk")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns system status and configuration information.

    Returns:
        dict: Health status with database info and service status
    """
    try:
        # Check database connectivity
        db = SessionLocal()
        try:
            db.execute("SELECT 1")
            db_status = "connected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        finally:
            db.close()

        # Check watch folder service status
        watch_folder_running = watch_service is not None and watch_service.is_running()

        return {
            "status": "healthy",
            "version": __version__,
            "database": db_status,
            "database_url": settings.database_url,
            "watch_folder_enabled": settings.enable_watch_folder,
            "watch_folder_running": watch_folder_running,
            "watch_folder_path": str(settings.slabcrop_output_folder)
            if settings.enable_watch_folder
            else None,
            "public_base_url": settings.public_base_url,
            "debug": settings.debug,
            "root": settings.slabhub_root,
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


# Additional health endpoints for granular checks

@app.get("/health/db", include_in_schema=False)
async def health_db():
    """
    Database health endpoint.
    Checks database connectivity and returns status.
    """
    try:
        db = SessionLocal()
        try:
            db.execute("SELECT 1")
            status = "connected"
        except Exception as e:
            status = f"error: {str(e)}"
        finally:
            db.close()
        return {"database": status}
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {"database": f"error: {str(e)}"}


@app.get("/health/storage", include_in_schema=False)
async def health_storage():
    """
    Storage health endpoint.
    Checks available disk space for the configured root directory.
    """
    try:
        total, used, free = shutil.disk_usage(settings.slabhub_root)
        return {
            "storage_total_bytes": total,
            "storage_used_bytes": used,
            "storage_free_bytes": free,
        }
    except Exception as e:
        logger.error(f"Storage health check failed: {e}", exc_info=True)
        return {"storage": f"error: {str(e)}"}


@app.get("/health/queue", include_in_schema=False)
async def health_queue():
    """
    Queue health endpoint.
    Since a queue system is not yet implemented, this returns a stub status.
    """
    return {"queue": "not implemented"}


# ============================================================================
# Short URL Redirect (for QR codes)
# ============================================================================

@app.get("/s/{public_id}", include_in_schema=False)
async def short_url_redirect(public_id: str):
    """
    Short URL redirect for QR codes.

    Redirects /s/{public_id} to /kiosk/slab/{public_id}

    Args:
        public_id: Slab public identifier

    Returns:
        Redirect to kiosk slab detail page
    """
    return RedirectResponse(url=f"/kiosk/slab/{public_id}")


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """
    Custom 404 handler.

    Always returns a JSON response with proper status code for APIs and redirects
    to the kiosk for other routes.
    """
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Not found", "path": request.url.path},
        )
    return RedirectResponse(url="/kiosk")


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """
    Custom 500 handler.
    Logs the error and returns a JSON response with a 500 status code.
    """
    logger.error(f"Internal server error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "path": request.url.path},
    )


# ============================================================================
# Development Server
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("Starting development server...")
    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
