"""
Watch folder service for SlabCrop integration.

This module provides a file system observer that watches a directory for new images,
validates them, and triggers processing callbacks. Uses the watchdog library to monitor
file system events and ensures files are completely written before processing.
"""

import logging
import time
from pathlib import Path
from typing import Callable, Set, Optional

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from backend.app.config import settings
from backend.app.utils import validate_image

logger = logging.getLogger(__name__)


class SlabCropEventHandler(FileSystemEventHandler):
    """
    File system event handler for SlabCrop image processing.

    Monitors a directory for new image files, validates them, and triggers
    a callback for valid images. Handles file completion detection and
    prevents duplicate processing.
    """

    # Supported image file extensions
    IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.bmp'}

    def __init__(self, callback: Callable[[Path], None]):
        """
        Initialize the event handler.

        Args:
            callback: Function to call with valid image paths.
                     Should accept a Path object as parameter.
        """
        super().__init__()
        self.callback = callback
        self.processing_files: Set[str] = set()
        logger.info("SlabCropEventHandler initialized")

    def on_created(self, event: FileSystemEvent) -> None:
        """
        Handle file creation events.

        Called when a new file is created in the watched directory.
        Only processes image files that pass validation.

        Args:
            event: The file system event containing the file path
        """
        # Ignore directory creation events
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Check if file has an image extension
        if file_path.suffix.lower() not in self.IMAGE_EXTENSIONS:
            logger.debug(f"Ignoring non-image file: {file_path.name}")
            return

        # Check if file is already being processed
        file_key = str(file_path.absolute())
        if file_key in self.processing_files:
            logger.debug(f"File already being processed: {file_path.name}")
            return

        # Mark file as being processed
        self.processing_files.add(file_key)

        try:
            logger.info(f"New image detected: {file_path.name}")

            # Wait for file to be completely written
            if not self._wait_for_file_complete(file_path):
                logger.warning(f"File did not stabilize within timeout: {file_path.name}")
                return

            # Validate the image
            validation_result = validate_image(
                file_path,
                min_width=settings.image_min_width,
                min_height=settings.image_min_height,
                max_size_mb=settings.max_image_size_mb,
                check_corruption=True
            )

            if not validation_result.valid:
                logger.warning(
                    f"Image validation failed for {file_path.name}: {validation_result.reason}"
                )
                return

            # Image is valid, trigger callback
            logger.info(f"Image validation passed, processing: {file_path.name}")
            try:
                self.callback(file_path)
            except Exception as e:
                logger.error(f"Error in callback for {file_path.name}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error processing file {file_path.name}: {e}", exc_info=True)

        finally:
            # Remove from processing set
            self.processing_files.discard(file_key)

    def _wait_for_file_complete(
        self,
        file_path: Path,
        stable_time: int = 2,
        max_wait: int = 30,
        check_interval: float = 0.5
    ) -> bool:
        """
        Wait for a file to be completely written.

        Monitors file size stability to determine when a file has finished
        being written. This prevents processing incomplete files.

        Args:
            file_path: Path to the file to monitor
            stable_time: Seconds file size must remain stable (default: 2)
            max_wait: Maximum seconds to wait for stability (default: 30)
            check_interval: Seconds between size checks (default: 0.5)

        Returns:
            True if file is complete and stable, False if timeout occurred
        """
        logger.debug(f"Waiting for file completion: {file_path.name}")

        start_time = time.time()
        last_size = -1
        stable_since = None

        while time.time() - start_time < max_wait:
            try:
                # Check if file still exists
                if not file_path.exists():
                    logger.warning(f"File disappeared during wait: {file_path.name}")
                    return False

                # Get current file size
                current_size = file_path.stat().st_size

                # Check if size has changed
                if current_size != last_size:
                    # Size changed, reset stability timer
                    last_size = current_size
                    stable_since = time.time()
                    logger.debug(
                        f"File size changed to {current_size} bytes: {file_path.name}"
                    )
                else:
                    # Size is stable, check if stable long enough
                    if stable_since is not None:
                        stable_duration = time.time() - stable_since
                        if stable_duration >= stable_time:
                            logger.debug(
                                f"File stable for {stable_duration:.1f}s "
                                f"({current_size} bytes): {file_path.name}"
                            )
                            return True

                # Wait before next check
                time.sleep(check_interval)

            except OSError as e:
                logger.error(f"Error checking file size for {file_path.name}: {e}")
                time.sleep(check_interval)

        # Timeout occurred
        elapsed = time.time() - start_time
        logger.warning(
            f"File stability timeout after {elapsed:.1f}s: {file_path.name}"
        )
        return False


class WatchFolderService:
    """
    Watch folder service for monitoring directory changes.

    Manages a watchdog Observer that monitors a directory for new files
    and triggers event handlers when files are created.
    """

    def __init__(self, watch_path: Path, callback: Callable[[Path], None]):
        """
        Initialize the watch folder service.

        Args:
            watch_path: Directory path to monitor
            callback: Function to call for valid images
        """
        self.watch_path = Path(watch_path)
        self.callback = callback
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[SlabCropEventHandler] = None

        # Create watch directory if it doesn't exist
        if not self.watch_path.exists():
            logger.info(f"Creating watch directory: {self.watch_path}")
            self.watch_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"WatchFolderService initialized for: {self.watch_path}")

    def start(self) -> None:
        """
        Start the watch folder service.

        Creates and starts a watchdog Observer to monitor the directory.
        This method is non-blocking and returns immediately.

        Raises:
            RuntimeError: If service is already running
        """
        if self.is_running():
            raise RuntimeError("Watch folder service is already running")

        logger.info(f"Starting watch folder service for: {self.watch_path}")

        # Create event handler
        self.event_handler = SlabCropEventHandler(self.callback)

        # Create and configure observer
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.watch_path),
            recursive=False  # Only watch the top-level directory
        )

        # Start observer thread
        self.observer.start()
        logger.info("Watch folder service started successfully")

    def stop(self) -> None:
        """
        Stop the watch folder service gracefully.

        Stops the observer and waits for it to finish processing.
        Safe to call even if service is not running.
        """
        if not self.is_running():
            logger.warning("Watch folder service is not running")
            return

        logger.info("Stopping watch folder service...")

        try:
            # Stop observer and wait for thread to finish
            self.observer.stop()
            self.observer.join(timeout=5.0)

            # Clean up references
            self.observer = None
            self.event_handler = None

            logger.info("Watch folder service stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping watch folder service: {e}", exc_info=True)
            # Force cleanup even on error
            self.observer = None
            self.event_handler = None

    def is_running(self) -> bool:
        """
        Check if the watch folder service is currently running.

        Returns:
            True if service is running, False otherwise
        """
        return self.observer is not None and self.observer.is_alive()


# Singleton instance
_watch_service_instance: Optional[WatchFolderService] = None


def get_watch_service(callback: Callable[[Path], None]) -> WatchFolderService:
    """
    Get or create the singleton watch folder service instance.

    This ensures only one watch service is running at a time for the
    configured SlabCrop output folder.

    Args:
        callback: Function to call for valid images

    Returns:
        WatchFolderService instance
    """
    global _watch_service_instance

    if _watch_service_instance is None:
        watch_path = Path(settings.slabcrop_output_folder)
        _watch_service_instance = WatchFolderService(watch_path, callback)
        logger.info("Created singleton WatchFolderService instance")

    return _watch_service_instance
