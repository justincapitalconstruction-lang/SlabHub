#!/usr/bin/env python3
"""
SlabHub Service Startup Script

Standalone script to start all SlabHub services with proper logging,
error handling, and graceful shutdown.

Usage:
    python scripts/start_services.py
    python scripts/start_services.py --no-watch  # Disable watch folder
    python scripts/start_services.py --debug     # Enable debug mode

Features:
    - Starts FastAPI server (uvicorn)
    - Optionally starts watch folder service
    - Comprehensive logging
    - Graceful shutdown handling (Ctrl+C)
    - Health check verification
    - Automatic directory creation
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings
from backend.app.core.drive_validator import enforce_drive_policy_at_startup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

logger = logging.getLogger(__name__)


class ServiceManager:
    """Manages SlabHub service lifecycle"""

    def __init__(self, enable_watch: bool = True, debug: bool = False):
        """
        Initialize service manager.

        Args:
            enable_watch: Enable watch folder service
            debug: Enable debug mode with auto-reload
        """
        self.enable_watch = enable_watch
        self.debug = debug
        self.server_process = None
        self.shutting_down = False

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals (Ctrl+C, SIGTERM)"""
        if not self.shutting_down:
            logger.info("\nReceived shutdown signal, stopping services...")
            self.shutting_down = True
            self.stop()
            sys.exit(0)

    def _create_directories(self):
        """Create required directories if they don't exist"""
        logger.info("Creating required directories...")

        directories = [
            Path(settings.slabcrop_output_folder),
            Path(settings.slabcrop_inbox_folder),
            Path(settings.incoming_raw_folder),
            Path(settings.processed_archive_folder),
            Path(settings.label_output_folder),
            Path(settings.qr_output_folder),
        ]

        # Create log directory
        if settings.log_file:
            log_dir = Path(settings.log_file).parent
            directories.append(log_dir)

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"  ✓ {directory}")
            except Exception as e:
                logger.warning(f"  ✗ Failed to create {directory}: {e}")

        logger.info("Directories created successfully")

    def _verify_config(self):
        """Verify critical configuration settings"""
        logger.info("Verifying configuration...")

        issues = []

        # Check database path
        db_path = settings.database_url.replace('sqlite:///', '')
        db_dir = Path(db_path).parent
        if not db_dir.exists():
            issues.append(f"Database directory does not exist: {db_dir}")

        # Check SlabCrop output folder if watch enabled
        if self.enable_watch and settings.enable_watch_folder:
            slabcrop_path = Path(settings.slabcrop_output_folder)
            if not slabcrop_path.exists():
                logger.warning(
                    f"SlabCrop output folder does not exist: {slabcrop_path}"
                )
                logger.warning("Creating folder...")
                try:
                    slabcrop_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    issues.append(f"Cannot create SlabCrop folder: {e}")

        # Check for .env file
        env_file = Path('.env')
        if not env_file.exists():
            logger.warning("No .env file found, using default configuration")

        if issues:
            logger.error("Configuration issues found:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False

        # Display configuration
        logger.info("Configuration verified:")
        logger.info(f"  Database: {settings.database_url}")
        logger.info(f"  Host: {settings.host}:{settings.port}")
        logger.info(f"  Public URL: {settings.public_base_url}")
        logger.info(f"  Watch Folder: {settings.enable_watch_folder and self.enable_watch}")
        if settings.enable_watch_folder and self.enable_watch:
            logger.info(f"  SlabCrop Output: {settings.slabcrop_output_folder}")
        logger.info(f"  Debug Mode: {self.debug or settings.debug}")

        return True

    def _wait_for_server(self, max_wait: int = 10):
        """
        Wait for server to be ready.

        Args:
            max_wait: Maximum seconds to wait

        Returns:
            True if server is ready, False otherwise
        """
        import urllib.request
        import urllib.error

        health_url = f"http://{settings.host}:{settings.port}/health"
        # Use localhost instead of 0.0.0.0 for health check
        if settings.host == "0.0.0.0":
            health_url = f"http://localhost:{settings.port}/health"

        logger.info(f"Waiting for server to be ready at {health_url}...")

        for i in range(max_wait):
            try:
                response = urllib.request.urlopen(health_url, timeout=1)
                if response.status == 200:
                    logger.info("✓ Server is ready!")
                    return True
            except (urllib.error.URLError, urllib.error.HTTPError, ConnectionRefusedError):
                time.sleep(1)
                logger.debug(f"  Waiting... ({i + 1}/{max_wait})")

        logger.warning("Server did not respond within timeout")
        return False

    def start(self):
        """Start all services"""
        logger.info("=" * 70)
        logger.info("SlabHub Service Manager")
        logger.info("=" * 70)

        # Create directories
        self._create_directories()

        # Verify configuration
        if not self._verify_config():
            logger.error("Configuration verification failed!")
            logger.error("Please check your .env file and fix the issues above.")
            return False

        logger.info("")
        logger.info("=" * 70)
        logger.info("Starting SlabHub Services...")
        logger.info("=" * 70)
        logger.info("")

        try:
            # Start uvicorn server
            import uvicorn

            logger.info("Starting FastAPI server with uvicorn...")
            logger.info(f"Server will be available at: http://{settings.host}:{settings.port}")
            logger.info(f"Public URL: {settings.public_base_url}")
            logger.info("")
            logger.info("Endpoints:")
            logger.info(f"  - Admin Interface: http://localhost:{settings.port}/admin")
            logger.info(f"  - Kiosk Interface: http://localhost:{settings.port}/kiosk")
            logger.info(f"  - API Documentation: http://localhost:{settings.port}/docs")
            logger.info(f"  - Health Check: http://localhost:{settings.port}/health")
            logger.info("")
            logger.info("Press Ctrl+C to stop all services")
            logger.info("=" * 70)
            logger.info("")

            # Override settings if specified
            if self.debug:
                reload = True
                log_level = "debug"
            else:
                reload = settings.debug
                log_level = settings.log_level.lower()

            # Start uvicorn server (blocking call)
            uvicorn.run(
                "backend.app.main:app",
                host=settings.host,
                port=settings.port,
                reload=reload,
                log_level=log_level,
                access_log=True,
            )

        except KeyboardInterrupt:
            logger.info("\nReceived keyboard interrupt")
        except Exception as e:
            logger.error(f"Error starting services: {e}", exc_info=True)
            return False

        return True

    def stop(self):
        """Stop all services gracefully"""
        logger.info("Stopping services...")

        # Uvicorn handles its own shutdown when interrupted
        # Watch folder service is managed by FastAPI lifespan in main.py

        logger.info("All services stopped")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Start SlabHub services',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default settings
  python scripts/start_services.py

  # Start without watch folder
  python scripts/start_services.py --no-watch

  # Start in debug mode with auto-reload
  python scripts/start_services.py --debug

  # Combine options
  python scripts/start_services.py --debug --no-watch

Notes:
  - Press Ctrl+C to stop services
  - Watch folder can also be disabled via .env: ENABLE_WATCH_FOLDER=false
  - Debug mode enables auto-reload on code changes
  - Logs are written to configured log file and console
        """
    )

    parser.add_argument(
        '--no-watch',
        action='store_true',
        help='Disable watch folder service (overrides .env setting)',
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode with auto-reload',
    )

    return parser.parse_args()


def check_python_version():
    """Verify Python version is adequate"""
    if sys.version_info < (3, 10):
        logger.error("Python 3.10 or higher is required")
        logger.error(f"Current version: {sys.version}")
        return False
    return True


def check_dependencies():
    """Verify required dependencies are installed"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'pydantic',
        'pillow',
        'qrcode',
        'reportlab',
        'watchdog',
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        logger.error("Missing required dependencies:")
        for package in missing:
            logger.error(f"  - {package}")
        logger.error("")
        logger.error("Install missing dependencies with:")
        logger.error("  pip install -r requirements.txt")
        return False

    return True


def main():
    """Main entry point"""
    # Parse arguments
    args = parse_args()

    # Display banner
    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                                                                  ║")
    print("║                    SlabHub Service Manager                       ║")
    print("║          Stone Slab Inventory Management System                 ║")
    print("║                                                                  ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print()

    # Check Python version
    if not check_python_version():
        return 1

    # Check dependencies
    logger.info("Checking dependencies...")
    if not check_dependencies():
        return 1
    logger.info("✓ All dependencies installed")
    logger.info("")

    # Validate drive policy BEFORE starting services
    logger.info("Validating drive policy...")
    try:
        enforce_drive_policy_at_startup(settings)
    except SystemExit:
        logger.error("Drive policy validation failed. Aborting startup.")
        logger.error("See DRIVE_POLICY.md for details on configuring paths.")
        return 1

    # Create service manager
    enable_watch = not args.no_watch
    manager = ServiceManager(enable_watch=enable_watch, debug=args.debug)

    # Start services
    success = manager.start()

    # Shutdown
    logger.info("")
    logger.info("=" * 70)
    logger.info("SlabHub Services Stopped")
    logger.info("=" * 70)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
