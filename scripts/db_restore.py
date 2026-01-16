#!/usr/bin/env python3
"""
Database Restore Script

Restores SQLite database from backup with:
- Backup verification before restore
- Support for compressed (.gz) and uncompressed backups
- Dry-run mode for preview
- Automatic backup of current database before restore

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
from datetime import datetime
from typing import Tuple, Optional

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


def is_compressed_backup(backup_path: Path) -> bool:
    """Check if a backup file is gzip compressed."""
    return backup_path.suffix == ".gz" or str(backup_path).endswith(".db.gz")


def decompress_backup(backup_path: Path, output_path: Path) -> bool:
    """
    Decompress a gzip backup file.

    Returns True on success, False on failure.
    """
    try:
        with gzip.open(backup_path, "rb") as f_in:
            with open(output_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        return True
    except Exception as e:
        logger.error(f"Decompression failed: {e}")
        return False


def verify_backup(backup_path: Path) -> Tuple[bool, str, dict]:
    """
    Verify a backup file is valid.

    Returns (success, message, info) tuple.
    """
    info = {
        "path": str(backup_path),
        "size_bytes": None,
        "compressed": False,
        "decompressed_size_bytes": None,
        "hash": None
    }

    if not backup_path.exists():
        return False, f"Backup file not found: {backup_path}", info

    info["size_bytes"] = backup_path.stat().st_size
    info["compressed"] = is_compressed_backup(backup_path)
    info["hash"] = compute_file_hash(backup_path)

    if info["compressed"]:
        # For compressed backups, decompress to temp and verify
        import tempfile

        logger.info("Decompressing backup for verification...")
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            if not decompress_backup(backup_path, tmp_path):
                return False, "Failed to decompress backup", info

            info["decompressed_size_bytes"] = tmp_path.stat().st_size

            logger.info("Verifying decompressed database integrity...")
            success, msg = verify_sqlite_integrity(tmp_path)

            if not success:
                return False, f"Backup integrity check failed: {msg}", info

            return True, "Backup verification successful", info

        finally:
            # Clean up temp file
            if tmp_path.exists():
                tmp_path.unlink()
    else:
        # Verify uncompressed backup directly
        logger.info("Verifying backup integrity...")
        success, msg = verify_sqlite_integrity(backup_path)

        if not success:
            return False, f"Backup integrity check failed: {msg}", info

        return True, "Backup verification successful", info


def create_pre_restore_backup(db_path: Path, backup_dir: Path) -> Optional[Path]:
    """
    Create a backup of the current database before restore.

    Returns the backup path or None on failure.
    """
    if not db_path.exists():
        logger.info("No existing database to backup")
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"slabhub_pre_restore_{timestamp}.db"
    backup_path = backup_dir / backup_name

    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f"Created pre-restore backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create pre-restore backup: {e}")
        return None


def restore_database(
    backup_path: Path,
    db_path: Path,
    backup_current: bool = True,
    backup_dir: Path = None,
    verify: bool = True,
    dry_run: bool = False
) -> Tuple[bool, dict]:
    """
    Restore database from backup.

    Returns (success, metadata) tuple.
    """
    metadata = {
        "backup_path": str(backup_path),
        "target_path": str(db_path),
        "restored_at": None,
        "pre_restore_backup": None,
        "verified": False,
        "dry_run": dry_run
    }

    # Verify backup first
    if verify:
        logger.info("Verifying backup before restore...")
        success, msg, info = verify_backup(backup_path)
        if not success:
            logger.error(f"Backup verification failed: {msg}")
            return False, metadata
        metadata["verified"] = True
        logger.info("Backup verified successfully")

    if dry_run:
        logger.info("DRY RUN: Would restore database")
        logger.info(f"  Source: {backup_path}")
        logger.info(f"  Target: {db_path}")
        if backup_current and db_path.exists():
            logger.info("  Would create pre-restore backup of current database")
        return True, metadata

    # Create backup of current database
    if backup_current and db_path.exists():
        backup_dir = backup_dir or DEFAULT_BACKUP_DIR
        pre_backup = create_pre_restore_backup(db_path, backup_dir)
        if pre_backup:
            metadata["pre_restore_backup"] = str(pre_backup)
        else:
            logger.warning("Failed to backup current database, proceeding with restore")

    # Ensure target directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if is_compressed_backup(backup_path):
            # Decompress and restore
            logger.info("Decompressing and restoring backup...")
            if not decompress_backup(backup_path, db_path):
                return False, metadata
        else:
            # Copy uncompressed backup
            logger.info("Restoring backup...")
            shutil.copy2(backup_path, db_path)

        metadata["restored_at"] = datetime.now().isoformat()

        # Verify restored database
        if verify:
            logger.info("Verifying restored database...")
            success, msg = verify_sqlite_integrity(db_path)
            if not success:
                logger.error(f"Restored database integrity check failed: {msg}")
                # Try to recover from pre-restore backup
                if metadata.get("pre_restore_backup"):
                    logger.info("Attempting to recover from pre-restore backup...")
                    shutil.copy2(Path(metadata["pre_restore_backup"]), db_path)
                return False, metadata
            logger.info("Restored database verified successfully")

        return True, metadata

    except Exception as e:
        logger.error(f"Restore failed: {e}")
        # Try to recover from pre-restore backup
        if metadata.get("pre_restore_backup"):
            logger.info("Attempting to recover from pre-restore backup...")
            try:
                shutil.copy2(Path(metadata["pre_restore_backup"]), db_path)
                logger.info("Recovery successful")
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {recovery_error}")
        return False, metadata


def list_available_backups(backup_dir: Path) -> list:
    """List available backup files."""
    backups = []

    if not backup_dir.exists():
        return backups

    for pattern in ["slabhub_backup_*.db", "slabhub_backup_*.db.gz"]:
        for file_path in backup_dir.glob(pattern):
            try:
                name = file_path.name
                timestamp_str = name.replace("slabhub_backup_", "").split(".")[0]
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                backups.append({
                    "path": file_path,
                    "timestamp": timestamp,
                    "size": file_path.stat().st_size,
                    "compressed": is_compressed_backup(file_path)
                })
            except ValueError:
                continue

    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return backups


def print_backup_list(backup_dir: Path):
    """Print list of available backups."""
    backups = list_available_backups(backup_dir)

    if not backups:
        print("No backups found")
        return

    print(f"\nAvailable backups in {backup_dir}:")
    print("-" * 80)
    print(f"{'#':<4} {'Filename':<45} {'Created':<20} {'Size':<12}")
    print("-" * 80)

    for i, backup in enumerate(backups, 1):
        size = backup["size"]
        size_str = f"{size / 1024 / 1024:.2f} MB" if size > 1024 * 1024 else f"{size / 1024:.1f} KB"
        compressed = " (gz)" if backup["compressed"] else ""
        print(f"{i:<4} {backup['path'].name:<45} {backup['timestamp'].strftime('%Y-%m-%d %H:%M:%S'):<20} {size_str:<12}{compressed}")

    print("-" * 80)
    print(f"Total: {len(backups)} backup(s)")
    print("\nUse --backup-file <filename> or --latest to restore")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database Restore for SlabHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python db_restore.py --list                            List available backups
  python db_restore.py --latest                          Restore most recent backup
  python db_restore.py --backup-file backup.db.gz       Restore specific backup
  python db_restore.py --latest --dry-run               Preview restore without changes
  python db_restore.py --latest --no-backup-current     Don't backup current database
        """
    )
    parser.add_argument(
        "--backup-file", "-f",
        type=Path,
        help="Path to backup file to restore"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Restore the most recent backup"
    )
    parser.add_argument(
        "--backup-dir", "-d",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"Backup directory (default: {DEFAULT_BACKUP_DIR})"
    )
    parser.add_argument(
        "--no-backup-current",
        action="store_true",
        help="Don't create backup of current database before restore"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip backup verification"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available backups"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--force", "-y",
        action="store_true",
        help="Skip confirmation prompt"
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
        version=f"SlabHub Database Restore v{load_version()}"
    )

    args = parser.parse_args()

    # Print version on startup
    version = load_version()
    print(f"SlabHub Database Restore v{version}")
    print("-" * 40)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Handle list command
    if args.list:
        print_backup_list(args.backup_dir)
        sys.exit(0)

    # Determine backup file to restore
    backup_path = None

    if args.backup_file:
        backup_path = args.backup_file
        if not backup_path.is_absolute():
            # Check if it's in backup_dir
            if (args.backup_dir / backup_path).exists():
                backup_path = args.backup_dir / backup_path
    elif args.latest:
        backups = list_available_backups(args.backup_dir)
        if not backups:
            logger.error("No backups found")
            sys.exit(1)
        backup_path = backups[0]["path"]
        logger.info(f"Selected most recent backup: {backup_path.name}")

    if not backup_path:
        parser.print_help()
        print("\nError: Must specify --backup-file or --latest")
        sys.exit(1)

    if not backup_path.exists():
        logger.error(f"Backup file not found: {backup_path}")
        sys.exit(1)

    # Get target database path
    try:
        db_path = get_database_path()
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Confirmation prompt
    if not args.force and not args.dry_run:
        print(f"\nWARNING: This will replace the current database!")
        print(f"  Backup: {backup_path}")
        print(f"  Target: {db_path}")
        if not args.no_backup_current:
            print("  (Current database will be backed up first)")

        response = input("\nContinue? [y/N]: ")
        if response.lower() != "y":
            print("Restore cancelled")
            sys.exit(0)

    # Perform restore
    success, metadata = restore_database(
        backup_path=backup_path,
        db_path=db_path,
        backup_current=not args.no_backup_current,
        backup_dir=args.backup_dir,
        verify=not args.no_verify,
        dry_run=args.dry_run
    )

    # Output results
    if args.json:
        import json
        output = {
            "action": "restore",
            "success": success,
            "metadata": metadata
        }
        print(json.dumps(output, indent=2))
    else:
        if success:
            print("\n" + "=" * 60)
            if args.dry_run:
                print("DRY RUN COMPLETE")
            else:
                print("RESTORE COMPLETE")
            print("=" * 60)
            print(f"Backup: {backup_path}")
            print(f"Target: {db_path}")
            if metadata.get("pre_restore_backup"):
                print(f"Pre-restore backup: {metadata['pre_restore_backup']}")
            print(f"Verified: {'Yes' if metadata.get('verified') else 'No'}")
            if metadata.get("restored_at"):
                print(f"Restored at: {metadata['restored_at']}")
            print("=" * 60)
        else:
            print("\nRestore FAILED. Check logs for details.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
