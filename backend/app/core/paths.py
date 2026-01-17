"""
Path utilities for SlabHub.

This module centralises path construction and validation. All file system paths should be generated
through these helper functions to ensure they are relative to the SlabHub root and to prevent
accidental writes outside of the allowed directory.
"""
from __future__ import annotations
import hashlib
import os
import shutil
from pathlib import Path
from typing import Optional

from backend.app.config import settings


def get_relative_path(path: str) -> str:
    """
    Validate that the given path is relative (not absolute) and normalised.
    Raises ValueError if an absolute path is supplied.
    """
    p = Path(path)
    if p.is_absolute():
        raise ValueError(f"Absolute paths are not allowed: {path}")
    return str(p)


def resolve_path(logical_path: str) -> Path:
    """
    Resolve a logical relative path into an absolute path within the configured SlabHub root.
    """
    rel = get_relative_path(logical_path)
    return Path(settings.slabhub_root).joinpath(rel).resolve()


def ensure_hash_filename(file_name: str) -> str:
    """
    Generate a deterministic hashed filename using SHA256 of the original filename.
    Preserves the original extension.
    """
    name = Path(file_name).name
    stem, ext = os.path.splitext(name)
    hash_digest = hashlib.sha256(stem.encode("utf-8")).hexdigest()[:16]
    return f"{hash_digest}{ext}"


def validate_file_exists(logical_path: str) -> bool:
    """
    Check whether a file exists at the given logical path.
    """
    return resolve_path(logical_path).exists()


def check_missing_files(db_session) -> list[str]:
    """
    Placeholder for checking DB references to files that no longer exist on disk.
    Returns a list of missing logical paths.
    """
    # This would scan database models for file paths and verify existence.
    # Implementation depends on the schema; to be filled in later.
    return []


def check_orphan_files(data_dir: Optional[Path] = None) -> list[str]:
    """
    Placeholder for detecting orphan files on disk that are not referenced in the DB.
    Returns a list of orphan logical paths.
    """
    # Implementation would list all files under data_dir and cross-check with DB.
    return []


def atomic_write(path: Path, data: bytes) -> None:
    """
    Write data to the given path atomically by writing to a temporary file first and renaming.
    """
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with open(temp_path, "wb") as f:
        f.write(data)
    os.replace(temp_path, path)


def disk_space_info() -> dict[str, int]:
    """
    Retrieve disk usage statistics for the SlabHub root directory.
    """
    total, used, free = shutil.disk_usage(settings.slabhub_root)
    return {"total": total, "used": used, "free": free}


def log_path_map(logger) -> None:
    """
    Log the mapping between logical directories and their absolute paths.
    """
    paths = {
        "slabcrop_output_folder": settings.slabcrop_output_folder,
        "slabcrop_inbox_folder": settings.slabcrop_inbox_folder,
        "incoming_raw_folder": settings.incoming_raw_folder,
        "processed_archive_folder": settings.processed_archive_folder,
        "label_output_folder": settings.label_output_folder,
        "qr_output_folder": settings.qr_output_folder,
        "log_file": settings.log_file,
    }
    logger.info("Path Map (logical → absolute):")
    for key, logical in paths.items():
        if logical:
            try:
                abs_path = resolve_path(str(logical))
            except Exception:
                abs_path = Path(logical).resolve()
            logger.info(f"  {key}: {logical} → {abs_path}")
