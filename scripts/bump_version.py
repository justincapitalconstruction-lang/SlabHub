#!/usr/bin/env python3
"""
Simple version bumping script for SlabHub.

This script reads the current version from the top-level VERSION file,
increments the major, minor or patch number, updates the VERSION file
and synchronizes the version in `backend/app/version.py`.

Usage:
    python scripts/bump_version.py [major|minor|patch]

Defaults to bumping the patch version if no argument is provided.
"""
import argparse
from pathlib import Path


def bump_version(part: str) -> str:
    version_file = Path(__file__).resolve().parents[1] / "VERSION"
    current = version_file.read_text().strip()
    parts = current.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid version format: {current}")
    major, minor, patch = map(int, parts)
    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    new_version = f"{major}.{minor}.{patch}"
    version_file.write_text(new_version)
    # also update backend/app/version.py
    version_py = Path(__file__).resolve().parents[1] / "backend" / "app" / "version.py"
    version_py.write_text(f'__version__ = "{new_version}"\n')
    return new_version


def main():
    parser = argparse.ArgumentParser(description="Bump the SlabHub project version")
    parser.add_argument(
        "part",
        nargs="?",
        default="patch",
        choices=["major", "minor", "patch"],
        help="Which part of the version to increment",
    )
    args = parser.parse_args()
    new_version = bump_version(args.part)
    print(f"Version bumped to {new_version}")


if __name__ == "__main__":
    main()
