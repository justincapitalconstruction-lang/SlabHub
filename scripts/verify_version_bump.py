#!/usr/bin/env python3
"""
Verify Version Bump Script

Ensures that VERSION.txt was modified whenever code files change.
Run this before merge/deployment to enforce version bumping.

Usage:
    python scripts/verify_version_bump.py
    python scripts/verify_version_bump.py --base main

Exit codes:
    0 - Version bump verified (or no code changes)
    1 - Code changed but VERSION.txt unchanged (FAIL)
    2 - Error during check
"""
import subprocess
import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION.txt"

# File patterns that require version bump
CODE_PATTERNS = [
    "backend/app/**/*.py",
    "backend/app/**/*.html",
    "scripts/*.py",
]

# Files that DON'T require version bump
IGNORE_PATTERNS = [
    "*.md",
    "*.txt",
    "*.json",
    ".env*",
    "*.bat",
    "*.sh",
    "__pycache__/**",
    "*.pyc",
    "data/**",
    "tests/**",
]


def get_changed_files(base_branch: str = "main") -> list[str]:
    """Get list of files changed compared to base branch."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_branch],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=30
        )
        if result.returncode != 0:
            # Try HEAD~1 as fallback
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1"],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                timeout=30
            )
        return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    except Exception as e:
        print(f"Error getting changed files: {e}")
        return []


def is_code_file(filepath: str) -> bool:
    """Check if a file is a code file that requires version bump."""
    # Check ignore patterns
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith("*"):
            if filepath.endswith(pattern[1:]):
                return False
        elif "**" in pattern:
            base = pattern.split("**")[0]
            if filepath.startswith(base):
                return False
        elif filepath == pattern or filepath.startswith(pattern.rstrip("/")):
            return False

    # Check code patterns
    for pattern in CODE_PATTERNS:
        if "**" in pattern:
            base = pattern.split("**")[0]
            suffix = pattern.split("**")[-1].lstrip("/").lstrip("*")
            if filepath.startswith(base) and filepath.endswith(suffix):
                return True
        elif "*" in pattern:
            base = pattern.split("*")[0]
            suffix = pattern.split("*")[-1]
            if filepath.startswith(base) and filepath.endswith(suffix):
                return True
        elif filepath == pattern:
            return True

    return False


def main(base_branch: str = "main") -> int:
    """
    Main verification logic.

    Returns:
        0 if version bump is valid
        1 if code changed without version bump
        2 if error occurred
    """
    print("=" * 60)
    print("SlabHub Version Bump Verification")
    print("=" * 60)

    # Check if VERSION.txt exists
    if not VERSION_FILE.exists():
        print(f"ERROR: VERSION.txt not found at {VERSION_FILE}")
        return 2

    current_version = VERSION_FILE.read_text().strip()
    print(f"Current version: {current_version}")

    # Get changed files
    changed_files = get_changed_files(base_branch)

    if not changed_files:
        print("No changed files detected.")
        return 0

    print(f"\nChanged files ({len(changed_files)}):")
    for f in changed_files[:10]:
        print(f"  - {f}")
    if len(changed_files) > 10:
        print(f"  ... and {len(changed_files) - 10} more")

    # Check for code changes
    code_files_changed = [f for f in changed_files if is_code_file(f)]
    version_changed = "VERSION.txt" in changed_files

    print(f"\nCode files changed: {len(code_files_changed)}")
    for f in code_files_changed[:5]:
        print(f"  - {f}")
    if len(code_files_changed) > 5:
        print(f"  ... and {len(code_files_changed) - 5} more")

    print(f"VERSION.txt changed: {version_changed}")

    # Verify
    if code_files_changed and not version_changed:
        print("\n" + "=" * 60)
        print("VERIFICATION FAILED")
        print("=" * 60)
        print("Code files were modified but VERSION.txt was NOT updated.")
        print("Please increment the version by +0.01 in VERSION.txt")
        print(f"Current version: {current_version}")
        print(f"Expected: Bump to next version (e.g., {current_version} -> {float(current_version) + 0.01:.2f})")
        return 1

    print("\n" + "=" * 60)
    print("VERIFICATION PASSED")
    print("=" * 60)

    if code_files_changed and version_changed:
        print("Code changes detected with corresponding version bump.")
    elif not code_files_changed:
        print("No code changes detected (only non-code files modified).")
    else:
        print("VERSION.txt updated without code changes (acceptable).")

    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Verify version bump for code changes")
    parser.add_argument("--base", default="main", help="Base branch to compare against")
    args = parser.parse_args()

    sys.exit(main(args.base))
