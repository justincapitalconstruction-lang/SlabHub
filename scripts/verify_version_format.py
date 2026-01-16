#!/usr/bin/env python3
"""
Verify Version Format Script

Ensures that version increments follow the +0.01 rule.
Checks that version format is valid and increment is exactly 0.01.

Usage:
    python scripts/verify_version_format.py
    python scripts/verify_version_format.py --previous 1.14 --current 1.15

Exit codes:
    0 - Version format is valid
    1 - Version format is invalid (FAIL)
    2 - Error during check
"""
import subprocess
import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = PROJECT_ROOT / "VERSION.txt"

# Valid version increment
VALID_INCREMENT = 0.01
TOLERANCE = 0.001  # Float comparison tolerance


def get_previous_version() -> str | None:
    """Get the previous version from git history."""
    try:
        result = subprocess.run(
            ["git", "show", "HEAD~1:VERSION.txt"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    # Try main branch
    try:
        result = subprocess.run(
            ["git", "show", "main:VERSION.txt"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return None


def parse_version(version_str: str) -> tuple[int, int] | None:
    """
    Parse version string into (major, minor) tuple.

    Args:
        version_str: Version like "1.14" or "2.03"

    Returns:
        Tuple (major, minor as int) or None if invalid
        e.g., "1.14" -> (1, 14)
    """
    try:
        version_str = version_str.strip()
        if "." not in version_str:
            return None

        parts = version_str.split(".")
        if len(parts) != 2:
            return None

        major = int(parts[0])
        # Handle minor as string to preserve leading zeros
        minor_str = parts[1]
        minor = int(minor_str)

        return (major, minor)
    except ValueError:
        return None


def validate_format(version_str: str) -> tuple[bool, str]:
    """
    Validate version string format.

    Valid formats: "1.01", "1.14", "2.00"
    Invalid formats: "1.1", "1.2.3", "v1.0", "1"

    Returns:
        Tuple (is_valid, message)
    """
    version_str = version_str.strip()

    if not version_str:
        return False, "Version string is empty"

    if version_str.startswith("v"):
        return False, "Version should not start with 'v'"

    if version_str.count(".") != 1:
        return False, "Version must have exactly one decimal point (e.g., 1.14)"

    parts = version_str.split(".")
    major_str, minor_str = parts

    # Validate major version
    try:
        major = int(major_str)
        if major < 0:
            return False, "Major version cannot be negative"
    except ValueError:
        return False, f"Major version '{major_str}' is not a valid integer"

    # Validate minor version
    try:
        minor = int(minor_str)
        if minor < 0:
            return False, "Minor version cannot be negative"
    except ValueError:
        return False, f"Minor version '{minor_str}' is not a valid integer"

    # Minor should be two digits for consistency
    if len(minor_str) != 2:
        return False, f"Minor version should be two digits (e.g., '01', '14'), got '{minor_str}'"

    return True, f"Valid version format: {major}.{minor:02d}"


def validate_increment(previous: str, current: str) -> tuple[bool, str]:
    """
    Validate that version increment is exactly +0.01.

    Returns:
        Tuple (is_valid, message)
    """
    prev_parsed = parse_version(previous)
    curr_parsed = parse_version(current)

    if prev_parsed is None:
        return False, f"Cannot parse previous version: {previous}"

    if curr_parsed is None:
        return False, f"Cannot parse current version: {current}"

    prev_major, prev_minor = prev_parsed
    curr_major, curr_minor = curr_parsed

    # Convert to comparable floats
    prev_val = prev_major + prev_minor / 100
    curr_val = curr_major + curr_minor / 100

    increment = curr_val - prev_val

    # Check if increment is exactly 0.01
    if abs(increment - VALID_INCREMENT) < TOLERANCE:
        return True, f"Valid increment: {previous} -> {current} (+0.01)"

    # Check for zero increment
    if abs(increment) < TOLERANCE:
        return True, f"No increment: {previous} -> {current} (version unchanged)"

    # Check for major version jump (requires approval)
    if curr_major > prev_major:
        return False, (
            f"Major version jump detected: {previous} -> {current}. "
            f"Major version changes require owner approval."
        )

    # Check for invalid increment
    if increment > VALID_INCREMENT + TOLERANCE:
        return False, (
            f"Invalid increment: {previous} -> {current} (+{increment:.2f}). "
            f"Version must increment by exactly +0.01."
        )

    if increment < 0:
        return False, (
            f"Version decreased: {previous} -> {current}. "
            f"Version cannot go backwards."
        )

    return False, (
        f"Invalid increment: {previous} -> {current} (+{increment:.4f}). "
        f"Version must increment by exactly +0.01."
    )


def main(previous: str | None = None, current: str | None = None) -> int:
    """
    Main verification logic.

    Returns:
        0 if version format is valid
        1 if version format is invalid
        2 if error occurred
    """
    print("=" * 60)
    print("SlabHub Version Format Verification")
    print("=" * 60)

    # Get current version
    if current is None:
        if not VERSION_FILE.exists():
            print(f"ERROR: VERSION.txt not found at {VERSION_FILE}")
            return 2
        current = VERSION_FILE.read_text().strip()

    print(f"Current version: {current}")

    # Validate current format
    is_valid, message = validate_format(current)
    if not is_valid:
        print(f"\nFORMAT ERROR: {message}")
        return 1
    print(f"Format check: {message}")

    # Get previous version if not provided
    if previous is None:
        previous = get_previous_version()

    if previous:
        print(f"Previous version: {previous}")

        # Validate increment
        is_valid, message = validate_increment(previous, current)
        if not is_valid:
            print(f"\nINCREMENT ERROR: {message}")
            return 1
        print(f"Increment check: {message}")
    else:
        print("Previous version: Not available (first version or no git history)")

    print("\n" + "=" * 60)
    print("VERIFICATION PASSED")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Verify version format and increment")
    parser.add_argument("--previous", help="Previous version to compare against")
    parser.add_argument("--current", help="Current version to validate")
    args = parser.parse_args()

    sys.exit(main(args.previous, args.current))
