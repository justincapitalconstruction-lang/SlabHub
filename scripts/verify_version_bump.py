#!/usr/bin/env python
"""
verify_version_bump.py

This script checks whether the SlabHub codebase has changed since the last run and ensures that the version number has been incremented accordingly.  It stores a simple state file (`.slabhub_state.json`) containing the last code hash and version.  If the code hash changes and the version remains the same, the script exits with an error message.

Usage:
    python scripts/verify_version_bump.py

Running this script will update the state file if the version bump is valid.
"""

import hashlib
import json
import os
from pathlib import Path
import sys


def compute_code_hash(paths):
    """Compute a SHA-256 hash of all files under the given directories."""
    hasher = hashlib.sha256()
    for base in paths:
        for file_path in base.rglob("*"):
            if file_path.is_file():
                # Skip database and compiled files
                if file_path.suffix in {".db", ".pyc"}:
                    continue
                with file_path.open("rb") as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        hasher.update(chunk)
    return hasher.hexdigest()


def load_version(version_file: Path) -> str:
    """Load the __version__ variable from a Python file."""
    version_ns = {}
    exec(version_file.read_text(), version_ns)
    return version_ns.get("__version__", "0.0.0")


def main() -> None:
    root = Path.cwd()
    app_dir = root / "backend" / "app"
    scripts_dir = root / "scripts"

    code_hash = compute_code_hash([app_dir, scripts_dir])

    version_file = app_dir / "version.py"
    current_version = load_version(version_file)

    state_file = root / ".slabhub_state.json"

    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            previous_hash = state.get("code_hash")
            previous_version = state.get("version")
            if previous_hash != code_hash and previous_version == current_version:
                print(
                    f"ERROR: Code has changed since last run but version {current_version} has not been bumped."
                )
                print(
                    "Please increment the version in backend/app/version.py before committing your changes."
                )
                sys.exit(1)
        except Exception:
            # If state file is corrupt, remove it and continue
            state_file.unlink(missing_ok=True)

    # Write new state
    state_file.write_text(json.dumps({"code_hash": code_hash, "version": current_version}, indent=2))
    print(
        f"Version {current_version} validated. State file updated with current code hash."
    )


if __name__ == "__main__":
    main()
