#!/usr/bin/env python3
"""
Database Backup Script

Creates SQLite database backups with:
- Timestamp-based naming
- Compression (gzip)
- Retention management (delete old backups)
- Integrity verification

SlabHub v1.12
"""

import sys
import os
import argparse
import logging
import gzip
import shutil
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import load_version, settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Default backup directory
DEFAULT_BACKUP_DIR = Path(__file__).parent.parent / "data" / "backups"

# Default retention period (days)
DEFAULT_RETENTION_DAYS = 30


def get_database_path() -> Path:
    """Extract database file path from connection URL."""
    db_url = settings.database_url

    if db_url.startswith("sqlite:///"):
        # Handle both relative and absolute paths
        path_str = db_url.replace("sqlite:///", "")
        path = Path(path_str)

        # If relative, resolve from project root
        if not path.is_absolute():
            project_root = Path(__file__).parent.parent
            path = project_root / path

        return path
    else:
        raise ValueError(f"Unsupported database URL format: {db_url}")


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def verify_sqlite_integrity(db_path: Path) -> Tuple[bool, str]:
    """
    Verify SQLite database integrity.

    Returns (success, message) tuple.
    """
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]

        conn.close()

        if result == "ok":
            return True, "Integrity check passed"
        else:
            return False, f"Integrity check failed: {result}"

    except Exception as e:
        return False, f"Integrity check error: {str(e)}"


def create_backup(
    db_path: Path,
    backup_dir: Path,
    compress: bool = True,
    verify: bool = True
) -> Tuple[bool, Path, dict]:
    """
    Create a database backup.

    Returns (success, backup_path, metadata) tuple.
    """
    metadata = {
        "source_path": str(db_path),
        "created_at": datetime.now().isoformat(),
        "version": load_version(),
        "compressed": compress,
        "verified": False,
        "source_hash": None,
        "backup_hash": None,
        "size_bytes": None,
        "compressed_size_bytes": None
    }

    # Ensure backup directory exists
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Check source database exists
    if not db_path.exists():
        logger.error(f"Source database not found: {db_path}")
        return False, None, metadata

    # Verify source integrity before backup
    if verify:
        logger.info("Verifying source database integrity...")
        success, msg = verify_sqlite_integrity(db_path)
        if not success:
            logger.error(f"Source database integrity check failed: {msg}")
            return False, None, metadata
        logger.info("Source database integrity verified")

    # Compute source hash
    metadata["source_hash"] = compute_file_hash(db_path)
    metadata["size_bytes"] = db_path.stat().st_size

    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"slabhub_backup_{timestamp}.db"
    if compress:
        backup_name += ".gz"

    backup_path = backup_dir / backup_name

    logger.info(f"Creating backup: {backup_path}")

    try:
        if compress:
            # Create compressed backup
            with open(db_path, "rb") as f_in:
                with gzip.open(backup_path, "wb", compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            metadata["compressed_size_bytes"] = backup_path.stat().st_size
        else:
            # Create uncompressed copy
            shutil.copy2(db_path, backup_path)

        metadata["backup_hash"] = compute_file_hash(backup_path)
        logger.info(f"Backup created successfully: {backup_path}")

        # Verify backup integrity
        if verify and not compress:
            logger.info("Verifying backup integrity...")
            success, msg = verify_sqlite_integrity(backup_path)
            if not success:
                logger.error(f"Backup integrity check failed: {msg}")
                return False, backup_path, metadata
            metadata["verified"] = True
            logger.info("Backup integrity verified")
        elif verify and compress:
            # For compressed backups, verify by decompressing and checking
            logger.info("Verifying compressed backup...")
            try:
                with gzip.open(backup_path, "rb") as f:
                    # Read first few bytes to verify it decompresses
                    f.read(1024)
                metadata["verified"] = True
                logger.info("Compressed backup verified")
            except Exception as e:
                logger.error(f"Compressed backup verification failed: {e}")
                return False, backup_path, metadata

        return True, backup_path, metadata

    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        # Clean up partial backup
        if backup_path.exists():
            backup_path.unlink()
        return False, None, metadata


def list_backups(backup_dir: Path) -> List[Tuple[Path, datetime]]:
    """
    List all backup files in the backup directory.

    Returns list of (path, timestamp) tuples sorted by timestamp descending.
    """
    backups = []

    if not backup_dir.exists():
        return backups

    for file_path in backup_dir.glob("slabhub_backup_*.db*"):
        # Extract timestamp from filename
        try:
            name = file_path.name
            # Format: slabhub_backup_YYYYMMDD_HHMMSS.db[.gz]
            timestamp_str = name.replace("slabhub_backup_", "").split(".")[0]
            timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            backups.append((file_path, timestamp))
        except ValueError:
            logger.warning(f"Could not parse timestamp from backup: {file_path}")
            continue

    # Sort by timestamp descending (newest first)
    backups.sort(key=lambda x: x[1], reverse=True)
    return backups


def cleanup_old_backups(backup_dir: Path, retention_days: int, dry_run: bool = False) -> List[Path]:
    """
    Delete backups older than retention period.

    Returns list of deleted backup paths.
    """
    deleted = []
    cutoff = datetime.now() - timedelta(days=retention_days)

    backups = list_backups(backup_dir)

    for backup_path, timestamp in backups:
        if timestamp < cutoff:
            if dry_run:
                logger.info(f"Would delete: {backup_path} (created {timestamp})")
            else:
                logger.info(f"Deleting old backup: {backup_path}")
                backup_path.unlink()
            deleted.append(backup_path)

    return deleted


def print_backup_list(backup_dir: Path):
    """Print list of available backups."""
    backups = list_backups(backup_dir)

    if not backups:
        print("No backups found")
        return

    print(f"\nAvailable backups in {backup_dir}:")
    print("-" * 70)
    print(f"{'Filename':<45} {'Created':<20} {'Size':<10}")
    print("-" * 70)

    for backup_path, timestamp in backups:
        size = backup_path.stat().st_size
        size_str = f"{size / 1024 / 1024:.2f} MB" if size > 1024 * 1024 else f"{size / 1024:.1f} KB"
        print(f"{backup_path.name:<45} {timestamp.strftime('%Y-%m-%d %H:%M:%S'):<20} {size_str:<10}")

    print("-" * 70)
    print(f"Total: {len(backups)} backup(s)")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database Backup for SlabHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python db_backup.py                     Create compressed backup
  python db_backup.py --no-compress       Create uncompressed backup
  python db_backup.py --list              List available backups
  python db_backup.py --cleanup           Delete old backups
  python db_backup.py --retention 7       Keep only 7 days of backups
        """
    )
    parser.add_argument(
        "--backup-dir", "-d",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"Backup directory (default: {DEFAULT_BACKUP_DIR})"
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Do not compress the backup"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip integrity verification"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available backups"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete backups older than retention period"
    )
    parser.add_argument(
        "--retention",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Retention period in days (default: {DEFAULT_RETENTION_DAYS})"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"SlabHub Database Backup v{load_version()}"
    )

    args = parser.parse_args()

    # Print version on startup
    version = load_version()
    print(f"SlabHub Database Backup v{version}")
    print("-" * 40)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle list command
    if args.list:
        print_backup_list(args.backup_dir)
        sys.exit(0)

    # Handle cleanup command
    if args.cleanup:
        logger.info(f"Cleaning up backups older than {args.retention} days...")
        deleted = cleanup_old_backups(args.backup_dir, args.retention, dry_run=args.dry_run)

        if args.json:
            import json
            output = {
                "action": "cleanup",
                "dry_run": args.dry_run,
                "retention_days": args.retention,
                "deleted_count": len(deleted),
                "deleted_files": [str(p) for p in deleted]
            }
            print(json.dumps(output, indent=2))
        else:
            if deleted:
                action = "Would delete" if args.dry_run else "Deleted"
                print(f"\n{action} {len(deleted)} old backup(s)")
            else:
                print("\nNo backups to clean up")

        sys.exit(0)

    # Create backup
    try:
        db_path = get_database_path()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    if args.dry_run:
        print(f"Would create backup of: {db_path}")
        print(f"Backup directory: {args.backup_dir}")
        print(f"Compression: {'disabled' if args.no_compress else 'enabled'}")
        sys.exit(0)

    success, backup_path, metadata = create_backup(
        db_path=db_path,
        backup_dir=args.backup_dir,
        compress=not args.no_compress,
        verify=not args.no_verify
    )

    # Output results
    if args.json:
        import json
        output = {
            "action": "backup",
            "success": success,
            "backup_path": str(backup_path) if backup_path else None,
            "metadata": metadata
        }
        print(json.dumps(output, indent=2))
    else:
        if success:
            print("\n" + "=" * 60)
            print("BACKUP COMPLETE")
            print("=" * 60)
            print(f"Source: {db_path}")
            print(f"Backup: {backup_path}")
            print(f"Size: {metadata.get('size_bytes', 0) / 1024 / 1024:.2f} MB")
            if metadata.get('compressed_size_bytes'):
                ratio = metadata['compressed_size_bytes'] / metadata['size_bytes'] * 100
                print(f"Compressed: {metadata['compressed_size_bytes'] / 1024 / 1024:.2f} MB ({ratio:.1f}%)")
            print(f"SHA256: {metadata.get('backup_hash', 'N/A')[:16]}...")
            print(f"Verified: {'Yes' if metadata.get('verified') else 'No'}")
            print("=" * 60)
        else:
            print("\nBackup FAILED. Check logs for details.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
