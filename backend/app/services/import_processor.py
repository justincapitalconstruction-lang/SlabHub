"""
Import processor service for SlabCrop image processing.

This module handles the processing of individual images including duplicate detection,
database record creation, file archiving, and import logging. Designed to work with
the watch folder service for automated image imports.
"""

import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import Slab, ImportLog
from backend.app.utils import calculate_perceptual_hash, is_duplicate

logger = logging.getLogger(__name__)


class ImportProcessor:
    """
    Processes imported images for the slab inventory system.

    Handles image validation, duplicate detection, database record creation,
    file archiving, and import logging. Designed to process images from the
    SlabCrop watch folder.
    """

    def __init__(self, db: Session, batch_id: Optional[str] = None):
        """
        Initialize the import processor.

        Args:
            db: SQLAlchemy database session
            batch_id: Optional batch ID for grouping imports.
                     If not provided, a new UUID-based batch ID is generated.
        """
        self.db = db
        self.batch_id = batch_id or self._generate_batch_id()

        # Initialize counters
        self.processed_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        self.errors: list[dict] = []

        # Create import log entry
        self.import_log = ImportLog(
            batch_id=self.batch_id,
            import_type="slabcrop_watch",
            source_path=str(settings.slabcrop_output_folder),
            status="running",
            items_processed=0,
            items_success=0,
            items_failed=0,
            items_skipped=0,
            errors=[],
            warnings=[]
        )
        self.db.add(self.import_log)
        self.db.commit()

        logger.info(f"ImportProcessor initialized with batch_id: {self.batch_id}")

    def _generate_batch_id(self) -> str:
        """
        Generate a unique batch ID with timestamp.

        Returns:
            Batch ID string in format: slabcrop_YYYYMMDD_HHMMSS_UUID
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"slabcrop_{timestamp}_{unique_id}"

    def process_image(self, image_path: Path) -> bool:
        """
        Process a single image file.

        Calculates perceptual hash, checks for duplicates, creates database
        record, and archives the file.

        Args:
            image_path: Path to the image file to process

        Returns:
            True if processing succeeded, False if failed or skipped
        """
        self.processed_count += 1

        try:
            logger.info(f"Processing image: {image_path.name}")

            # Calculate perceptual hash
            phash = calculate_perceptual_hash(image_path)
            if phash is None:
                error_msg = f"Failed to calculate perceptual hash: {image_path.name}"
                logger.error(error_msg)
                self._log_error(image_path, error_msg)
                self.failed_count += 1
                return False

            logger.debug(f"Calculated perceptual hash for {image_path.name}: {phash}")

            # Check for duplicates
            duplicate_slab = self._find_duplicate(phash)
            if duplicate_slab:
                logger.warning(
                    f"Duplicate image detected: {image_path.name} "
                    f"(matches slab {duplicate_slab.public_id})"
                )
                # Archive to duplicates folder
                self._archive_file(image_path, "duplicates")
                self.skipped_count += 1
                return False

            # Extract slab name from filename
            slab_name = self._extract_slab_name(image_path)

            # Generate unique public ID
            public_id = self._generate_public_id()

            # Archive file to processed folder (before creating DB record)
            archived_path = self._archive_file(image_path, "processed")
            if archived_path is None:
                error_msg = f"Failed to archive file: {image_path.name}"
                logger.error(error_msg)
                self._log_error(image_path, error_msg)
                self.failed_count += 1
                return False

            # Create Slab record
            slab = Slab(
                public_id=public_id,
                name=slab_name,
                primary_image=str(archived_path),
                perceptual_hash=phash,
                import_source="slabcrop_watch",
                import_batch_id=self.batch_id,
                status="available",
                quantity=1
            )

            self.db.add(slab)
            self.db.commit()

            logger.info(
                f"Successfully created slab record: {public_id} ({slab_name})"
            )
            self.success_count += 1
            return True

        except Exception as e:
            error_msg = f"Error processing {image_path.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._log_error(image_path, error_msg)
            self.failed_count += 1

            # Rollback transaction on error
            self.db.rollback()
            return False

        finally:
            # Update import log statistics
            self._update_import_log()

    def _find_duplicate(self, phash: str) -> Optional[Slab]:
        """
        Find duplicate slab by perceptual hash.

        Args:
            phash: Perceptual hash to search for

        Returns:
            Slab record if duplicate found, None otherwise
        """
        try:
            # Get all slabs with perceptual hashes
            slabs_with_hashes = self.db.query(Slab).filter(
                Slab.perceptual_hash.isnot(None)
            ).all()

            # Compare hashes using configured threshold
            threshold = settings.duplicate_threshold

            for slab in slabs_with_hashes:
                if is_duplicate(phash, slab.perceptual_hash, threshold=threshold):
                    logger.debug(
                        f"Found duplicate: {slab.public_id} (name: {slab.name})"
                    )
                    return slab

            return None

        except Exception as e:
            logger.error(f"Error finding duplicates: {e}", exc_info=True)
            return None

    def _extract_slab_name(self, image_path: Path) -> str:
        """
        Extract slab name from image filename.

        Removes file extension and cleans up the filename.

        Args:
            image_path: Path to the image file

        Returns:
            Cleaned slab name string
        """
        # Remove file extension
        name = image_path.stem

        # Replace underscores and hyphens with spaces
        name = name.replace('_', ' ').replace('-', ' ')

        # Clean up multiple spaces
        name = ' '.join(name.split())

        # Capitalize first letter of each word
        name = name.title()

        return name or "Unnamed Slab"

    def _archive_file(self, file_path: Path, subdir: str) -> Optional[Path]:
        """
        Archive file to the archive folder with date-based organization.

        Archives files to: archive_folder/subdir/YYYYMMDD/filename
        Handles filename conflicts by appending a counter.

        Args:
            file_path: Path to the file to archive
            subdir: Subdirectory name (e.g., 'processed' or 'duplicates')

        Returns:
            Path to archived file if successful, None if failed
        """
        try:
            # Build archive path with date subdirectory
            archive_base = Path(settings.processed_archive_folder)
            date_str = datetime.now().strftime("%Y%m%d")
            archive_dir = archive_base / subdir / date_str

            # Create archive directory
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Build destination path
            dest_path = archive_dir / file_path.name

            # Handle filename conflicts
            if dest_path.exists():
                counter = 1
                stem = file_path.stem
                suffix = file_path.suffix

                while dest_path.exists():
                    new_name = f"{stem}_{counter}{suffix}"
                    dest_path = archive_dir / new_name
                    counter += 1
                    if counter > 1000:  # Prevent infinite loops
                        logger.error(
                            f"Too many filename conflicts for {file_path.name}"
                        )
                        return None

                logger.debug(
                    f"Renamed {file_path.name} to {dest_path.name} "
                    f"to avoid conflict"
                )

            # Copy file to archive
            shutil.copy2(file_path, dest_path)
            logger.debug(f"Archived {file_path.name} to {dest_path}")

            # Delete original file
            file_path.unlink()
            logger.debug(f"Deleted original file: {file_path.name}")

            return dest_path

        except Exception as e:
            logger.error(
                f"Error archiving file {file_path.name}: {e}",
                exc_info=True
            )
            return None

    def _log_error(self, file_path: Path, error: str) -> None:
        """
        Log an error for a specific file.

        Args:
            file_path: Path to the file that caused the error
            error: Error message
        """
        error_entry = {
            "file": file_path.name,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self.errors.append(error_entry)
        logger.debug(f"Logged error for {file_path.name}: {error}")

    def _update_import_log(self) -> None:
        """
        Update import log statistics in the database.

        Updates the ImportLog record with current processing statistics.
        """
        try:
            self.import_log.items_processed = self.processed_count
            self.import_log.items_success = self.success_count
            self.import_log.items_failed = self.failed_count
            self.import_log.items_skipped = self.skipped_count
            self.import_log.errors = self.errors if self.errors else None

            self.db.commit()
            logger.debug("Updated import log statistics")

        except Exception as e:
            logger.error(f"Error updating import log: {e}", exc_info=True)
            self.db.rollback()

    def _generate_public_id(self) -> str:
        """
        Generate a unique public ID for a slab.

        Returns:
            Unique public ID string (8-character UUID)
        """
        while True:
            public_id = str(uuid.uuid4())[:8].upper()

            # Check if ID already exists
            existing = self.db.query(Slab).filter(
                Slab.public_id == public_id
            ).first()

            if not existing:
                return public_id

    def finalize(self) -> None:
        """
        Finalize the import process and complete the import log.

        Updates the import log status to 'completed' or 'failed' based on
        processing results and adds a summary.
        """
        try:
            # Determine final status
            if self.failed_count > 0 and self.success_count == 0:
                status = "failed"
            elif self.failed_count > 0:
                status = "partial"
            else:
                status = "completed"

            # Generate summary
            summary = (
                f"SlabCrop import completed. "
                f"Processed: {self.processed_count}, "
                f"Success: {self.success_count}, "
                f"Failed: {self.failed_count}, "
                f"Skipped (duplicates): {self.skipped_count}"
            )

            # Update import log
            self.import_log.status = status
            self.import_log.completed_at = datetime.now()
            self.import_log.summary = summary

            self.db.commit()

            logger.info(f"Import finalized: {summary}")

        except Exception as e:
            logger.error(f"Error finalizing import: {e}", exc_info=True)
            self.db.rollback()
