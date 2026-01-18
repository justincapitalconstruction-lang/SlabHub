"""
Drive validation utilities for SlabHub.

Enforces D:\\ drive policy for all file operations.
All application data MUST reside on D:\\ drive - writing to C:\\ is prohibited.

See DRIVE_POLICY.md for full documentation.
"""
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# Drive policy configuration
REQUIRED_DRIVE = "D:"
FORBIDDEN_DRIVES = ["C:"]


def validate_drive_policy(path: Path) -> Tuple[bool, Optional[str]]:
    """
    Validate that a path conforms to drive policy.

    Args:
        path: Path object to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if path is valid
        - (False, error_message) if path violates policy
    """
    if not path.is_absolute():
        return True, None  # Relative paths are OK - resolved against slabhub_root

    drive = path.drive.upper()

    if drive in FORBIDDEN_DRIVES:
        return False, f"Writing to {drive}\\ is prohibited by drive policy. Use D:\\ instead."

    return True, None


def validate_path_string(path_str: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a path string conforms to drive policy.

    Handles special cases like database URLs (sqlite:///...).

    Args:
        path_str: Path string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not path_str:
        return True, None

    # Handle database URLs
    if path_str.startswith("sqlite:///"):
        path_str = path_str.replace("sqlite:///", "")

    # Skip relative paths
    if path_str.startswith("./") or path_str.startswith("../"):
        return True, None

    return validate_drive_policy(Path(path_str))


def enforce_drive_policy_at_startup(settings) -> None:
    """
    Validate all configured paths at startup.

    Checks all path-related settings to ensure they conform to drive policy.
    Raises SystemExit if any policy violations are detected.

    Args:
        settings: The Settings object from config.py

    Raises:
        SystemExit: If any path violates drive policy
    """
    logger.info("Validating drive policy...")

    paths_to_check: List[Tuple[str, str]] = [
        ("slabhub_root", getattr(settings, 'slabhub_root', None)),
        ("slabcrop_output_folder", getattr(settings, 'slabcrop_output_folder', None)),
        ("slabcrop_inbox_folder", getattr(settings, 'slabcrop_inbox_folder', None)),
        ("incoming_raw_folder", getattr(settings, 'incoming_raw_folder', None)),
        ("processed_archive_folder", getattr(settings, 'processed_archive_folder', None)),
        ("label_output_folder", getattr(settings, 'label_output_folder', None)),
        ("qr_output_folder", getattr(settings, 'qr_output_folder', None)),
        ("log_file", getattr(settings, 'log_file', None)),
    ]

    # Also check database URL
    db_url = getattr(settings, 'database_url', None)
    if db_url and db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        paths_to_check.append(("database_url", db_path))

    violations: List[str] = []

    for name, path_str in paths_to_check:
        if not path_str:
            continue

        is_valid, error = validate_path_string(path_str)
        if not is_valid:
            violations.append(f"  - {name}: {error} (current: {path_str})")

    if violations:
        logger.critical("=" * 60)
        logger.critical("DRIVE POLICY VIOLATION DETECTED")
        logger.critical("=" * 60)
        logger.critical("SlabHub requires all data to reside on D:\\ drive.")
        logger.critical("The following paths violate this policy:")
        for v in violations:
            logger.critical(v)
        logger.critical("")
        logger.critical("To fix this issue:")
        logger.critical("1. Update your .env file to use D:\\ paths")
        logger.critical("2. Set SLABHUB_ROOT=D:/slabHub")
        logger.critical("3. See DRIVE_POLICY.md for full documentation")
        logger.critical("=" * 60)
        sys.exit(1)

    logger.info("Drive policy validation passed - all paths on D:\\ drive")


def get_safe_path(relative_path: str, settings) -> Path:
    """
    Convert a relative path to an absolute path under slabhub_root.

    This ensures all file operations stay within the D:\\ drive policy.

    Args:
        relative_path: Relative path (e.g., "./data/labels")
        settings: Settings object with slabhub_root

    Returns:
        Absolute Path object on D:\\ drive
    """
    root = Path(getattr(settings, 'slabhub_root', 'D:/slabHub'))

    if relative_path.startswith("./"):
        relative_path = relative_path[2:]
    elif relative_path.startswith("../"):
        # Don't allow escaping the root
        logger.warning(f"Attempted path escape: {relative_path}")
        relative_path = relative_path.replace("../", "")

    return root / relative_path
