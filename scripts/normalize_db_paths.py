#!/usr/bin/env python3
"""
Database Path Normalization Script

Finds all absolute paths in the database and converts them to logical paths.
Supports --dry-run mode to preview changes without modifying data.

SlabHub v1.12
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import load_version, settings
from backend.app.models import (
    SessionLocal, init_db,
    Slab, ImportLog
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PathNormalizationLog:
    """Tracks path normalization changes."""

    def __init__(self):
        self.changes: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.start_time: datetime = datetime.now()
        self.end_time: Optional[datetime] = None

    def add_change(self, table: str, record_id: int, field: str,
                   old_value: str, new_value: str, identifier: str = None):
        """Record a path change."""
        self.changes.append({
            "table": table,
            "record_id": record_id,
            "identifier": identifier,
            "field": field,
            "old_value": old_value,
            "new_value": new_value,
            "timestamp": datetime.now().isoformat()
        })

    def add_error(self, table: str, record_id: int, field: str,
                  error: str, identifier: str = None):
        """Record an error during normalization."""
        self.errors.append({
            "table": table,
            "record_id": record_id,
            "identifier": identifier,
            "field": field,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })

    def finalize(self):
        """Finalize the log."""
        self.end_time = datetime.now()

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        return {
            "total_changes": len(self.changes),
            "total_errors": len(self.errors),
            "tables_affected": list(set(c["table"] for c in self.changes)),
            "duration_seconds": (self.end_time - self.start_time).total_seconds() if self.end_time else None
        }

    def print_log(self, verbose: bool = False):
        """Print the normalization log."""
        self.finalize()
        summary = self.get_summary()

        print("\n" + "=" * 60)
        print("PATH NORMALIZATION LOG")
        print("=" * 60)
        print(f"Start time: {self.start_time.isoformat()}")
        print(f"Duration: {summary['duration_seconds']:.2f} seconds" if summary['duration_seconds'] else "N/A")
        print(f"Total changes: {summary['total_changes']}")
        print(f"Total errors: {summary['total_errors']}")
        print(f"Tables affected: {', '.join(summary['tables_affected']) if summary['tables_affected'] else 'None'}")
        print()

        if verbose and self.changes:
            print("-" * 60)
            print("CHANGES:")
            print("-" * 60)
            for change in self.changes:
                id_str = f" ({change['identifier']})" if change['identifier'] else ""
                print(f"\n[{change['table']}] ID {change['record_id']}{id_str}")
                print(f"  Field: {change['field']}")
                print(f"  Old: {change['old_value']}")
                print(f"  New: {change['new_value']}")

        if self.errors:
            print("\n" + "-" * 60)
            print("ERRORS:")
            print("-" * 60)
            for error in self.errors:
                id_str = f" ({error['identifier']})" if error['identifier'] else ""
                print(f"\n[{error['table']}] ID {error['record_id']}{id_str}")
                print(f"  Field: {error['field']}")
                print(f"  Error: {error['error']}")

        print("\n" + "=" * 60)


def get_slabhub_root() -> Path:
    """Get the SlabHub root path from settings."""
    return Path(settings.slabhub_root)


def normalize_to_logical_path(absolute_path: str) -> Optional[str]:
    """
    Convert an absolute path to a logical path relative to SlabHub root.

    Returns None if the path cannot be normalized.
    """
    if not absolute_path:
        return None

    path = Path(absolute_path)

    # Already a logical path (not absolute)
    if not path.is_absolute():
        return absolute_path

    root = get_slabhub_root()

    try:
        # Try to make relative to SlabHub root
        relative = path.relative_to(root)
        # Use forward slashes for consistency
        return str(relative).replace("\\", "/")
    except ValueError:
        # Path is not under SlabHub root, try common prefixes
        # Check if it starts with a known data directory
        path_str = str(path).replace("\\", "/")

        # Common patterns to normalize
        known_prefixes = [
            ("D:/slabHub/", ""),
            ("D:\\slabHub\\", ""),
            (str(root).replace("\\", "/") + "/", ""),
            (str(root) + "\\", ""),
        ]

        for prefix, replacement in known_prefixes:
            if path_str.startswith(prefix):
                return path_str[len(prefix):]

        # Cannot normalize
        return None


def is_absolute_path(path_str: str) -> bool:
    """Check if a path string represents an absolute path."""
    if not path_str:
        return False
    return Path(path_str).is_absolute()


def normalize_slab_paths(db, log: PathNormalizationLog, dry_run: bool = False) -> int:
    """Normalize paths in the slabs table."""
    logger.info("Normalizing slab paths...")
    changes_count = 0

    slabs = db.query(Slab).all()

    for slab in slabs:
        # Normalize primary_image
        if slab.primary_image and is_absolute_path(slab.primary_image):
            normalized = normalize_to_logical_path(slab.primary_image)
            if normalized and normalized != slab.primary_image:
                log.add_change(
                    "slabs", slab.id, "primary_image",
                    slab.primary_image, normalized,
                    identifier=slab.public_id
                )
                if not dry_run:
                    slab.primary_image = normalized
                changes_count += 1
            elif normalized is None:
                log.add_error(
                    "slabs", slab.id, "primary_image",
                    f"Cannot normalize path: {slab.primary_image}",
                    identifier=slab.public_id
                )

        # Normalize additional_images (JSON array)
        if slab.additional_images:
            new_images = []
            images_changed = False

            for i, img_path in enumerate(slab.additional_images):
                if img_path and is_absolute_path(img_path):
                    normalized = normalize_to_logical_path(img_path)
                    if normalized and normalized != img_path:
                        log.add_change(
                            "slabs", slab.id, f"additional_images[{i}]",
                            img_path, normalized,
                            identifier=slab.public_id
                        )
                        new_images.append(normalized)
                        images_changed = True
                        changes_count += 1
                    elif normalized is None:
                        log.add_error(
                            "slabs", slab.id, f"additional_images[{i}]",
                            f"Cannot normalize path: {img_path}",
                            identifier=slab.public_id
                        )
                        new_images.append(img_path)  # Keep original
                    else:
                        new_images.append(img_path)
                else:
                    new_images.append(img_path)

            if images_changed and not dry_run:
                slab.additional_images = new_images

        # Normalize qr_code_path
        if slab.qr_code_path and is_absolute_path(slab.qr_code_path):
            normalized = normalize_to_logical_path(slab.qr_code_path)
            if normalized and normalized != slab.qr_code_path:
                log.add_change(
                    "slabs", slab.id, "qr_code_path",
                    slab.qr_code_path, normalized,
                    identifier=slab.public_id
                )
                if not dry_run:
                    slab.qr_code_path = normalized
                changes_count += 1
            elif normalized is None:
                log.add_error(
                    "slabs", slab.id, "qr_code_path",
                    f"Cannot normalize path: {slab.qr_code_path}",
                    identifier=slab.public_id
                )

    return changes_count


def normalize_import_log_paths(db, log: PathNormalizationLog, dry_run: bool = False) -> int:
    """Normalize paths in the import_logs table."""
    logger.info("Normalizing import log paths...")
    changes_count = 0

    import_logs = db.query(ImportLog).all()

    for import_log in import_logs:
        if import_log.source_path and is_absolute_path(import_log.source_path):
            normalized = normalize_to_logical_path(import_log.source_path)
            if normalized and normalized != import_log.source_path:
                log.add_change(
                    "import_logs", import_log.id, "source_path",
                    import_log.source_path, normalized,
                    identifier=import_log.batch_id
                )
                if not dry_run:
                    import_log.source_path = normalized
                changes_count += 1
            elif normalized is None:
                log.add_error(
                    "import_logs", import_log.id, "source_path",
                    f"Cannot normalize path: {import_log.source_path}",
                    identifier=import_log.batch_id
                )

    return changes_count


def run_normalization(dry_run: bool = False, verbose: bool = False) -> Tuple[PathNormalizationLog, bool]:
    """Run path normalization on all tables."""
    log = PathNormalizationLog()
    success = True

    try:
        init_db()
        db = SessionLocal()

        try:
            # Normalize all tables
            slab_changes = normalize_slab_paths(db, log, dry_run=dry_run)
            import_changes = normalize_import_log_paths(db, log, dry_run=dry_run)

            total_changes = slab_changes + import_changes

            if not dry_run and total_changes > 0:
                logger.info(f"Committing {total_changes} changes...")
                db.commit()
                logger.info("Changes committed successfully")
            elif dry_run:
                logger.info(f"DRY RUN: Would make {total_changes} changes")
                db.rollback()
            else:
                logger.info("No changes needed")

        except Exception as e:
            logger.error(f"Error during normalization: {e}")
            db.rollback()
            log.add_error("SYSTEM", 0, "commit", str(e))
            success = False
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        log.add_error("SYSTEM", 0, "init", str(e))
        success = False

    return log, success


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database Path Normalization for SlabHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python normalize_db_paths.py --dry-run    Preview changes without modifying
  python normalize_db_paths.py              Apply normalization
  python normalize_db_paths.py --verbose    Show detailed changes
        """
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview changes without modifying the database"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output showing all changes"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"SlabHub Path Normalization v{load_version()}"
    )

    args = parser.parse_args()

    # Print version on startup
    version = load_version()
    print(f"SlabHub Path Normalization v{version}")
    if args.dry_run:
        print("*** DRY RUN MODE - No changes will be made ***")
    print("-" * 40)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run normalization
    log, success = run_normalization(dry_run=args.dry_run, verbose=args.verbose)

    # Output results
    if args.json:
        import json
        log.finalize()
        output = {
            "version": version,
            "dry_run": args.dry_run,
            "success": success,
            "summary": log.get_summary(),
            "changes": log.changes,
            "errors": log.errors
        }
        print(json.dumps(output, indent=2))
    else:
        log.print_log(verbose=args.verbose)

    if success:
        if args.dry_run:
            print(f"\nDRY RUN complete. {len(log.changes)} change(s) would be made.")
        else:
            print(f"\nNormalization complete. {len(log.changes)} change(s) applied.")
    else:
        print("\nNormalization completed with errors. Check log above.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
