#!/usr/bin/env python3
"""
Compute Code Hash Script

Generates a deterministic hash of the codebase for version enforcement.
Prefers git commit hash, falls back to file-based hashing.

Usage:
    python scripts/compute_code_hash.py
    python scripts/compute_code_hash.py --full  # Show full hash

Exit codes:
    0 - Success
    1 - Error
"""
import hashlib
import subprocess
import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Directories to include in hash
HASH_DIRS = [
    "backend/app",
]

# File extensions to hash
HASH_EXTENSIONS = {".py", ".html"}

# Files/directories to exclude
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    ".pyo",
    ".git",
    "data/",
    "tests/",
]


def get_git_hash() -> str | None:
    """Get the current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def compute_file_hash() -> str:
    """Compute hash from source files."""
    hasher = hashlib.sha256()

    for hash_dir in HASH_DIRS:
        dir_path = PROJECT_ROOT / hash_dir
        if not dir_path.exists():
            continue

        # Get all files sorted for deterministic ordering
        for file_path in sorted(dir_path.rglob("*")):
            # Skip directories
            if file_path.is_dir():
                continue

            # Skip excluded patterns
            str_path = str(file_path)
            if any(pattern in str_path for pattern in EXCLUDE_PATTERNS):
                continue

            # Only hash specific extensions
            if file_path.suffix not in HASH_EXTENSIONS:
                continue

            try:
                # Include relative path in hash for rename detection
                rel_path = file_path.relative_to(PROJECT_ROOT)
                hasher.update(str(rel_path).encode())
                hasher.update(file_path.read_bytes())
            except Exception:
                pass

    return hasher.hexdigest()


def main(full: bool = False) -> int:
    """
    Main function to compute and display code hash.

    Args:
        full: If True, show full hash; otherwise truncated

    Returns:
        0 on success, 1 on error
    """
    print("=" * 60)
    print("SlabHub Code Hash Computation")
    print("=" * 60)

    # Try git hash first
    git_hash = get_git_hash()
    if git_hash:
        print(f"Source: git commit")
        if full:
            print(f"Hash: {git_hash}")
        else:
            print(f"Hash: {git_hash[:16]}...")
        print(f"\nFull git hash: {git_hash}")
    else:
        print("Source: file-based (git not available)")

    # Always compute file hash for comparison
    file_hash = compute_file_hash()
    print(f"\nFile-based hash: {file_hash[:16]}..." if not full else f"\nFile-based hash: {file_hash}")

    # Report which hash would be used
    print("\n" + "-" * 60)
    if git_hash:
        active_hash = git_hash[:16]
        print(f"Active hash (used by startup guard): {active_hash}")
    else:
        active_hash = file_hash[:16]
        print(f"Active hash (used by startup guard): {active_hash}")

    # Show hash directories info
    print("\n" + "-" * 60)
    print("Hash includes files from:")
    for hash_dir in HASH_DIRS:
        dir_path = PROJECT_ROOT / hash_dir
        if dir_path.exists():
            file_count = sum(1 for f in dir_path.rglob("*")
                           if f.is_file() and f.suffix in HASH_EXTENSIONS
                           and not any(p in str(f) for p in EXCLUDE_PATTERNS))
            print(f"  - {hash_dir}/ ({file_count} files)")
        else:
            print(f"  - {hash_dir}/ (not found)")

    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Compute code hash for version enforcement")
    parser.add_argument("--full", action="store_true", help="Show full hash instead of truncated")
    args = parser.parse_args()

    sys.exit(main(args.full))
