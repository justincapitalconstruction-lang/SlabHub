#!/usr/bin/env python3
"""
Import Smoke Test for SlabHub

This script verifies that all core packages can be imported without errors.
Run this after any structural changes to validate import resolution.

Usage:
    python scripts/import_smoke_test.py
"""

import sys
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test all core package imports."""
    errors = []

    # Test schemas
    try:
        from backend.app.schemas import SlabCreate, SlabUpdate, SlabResponse
        print("[OK] backend.app.schemas")
    except ImportError as e:
        errors.append(f"[FAIL] backend.app.schemas: {e}")

    # Test models
    try:
        from backend.app.models import Slab, Base, get_db, init_db
        print("[OK] backend.app.models")
    except ImportError as e:
        errors.append(f"[FAIL] backend.app.models: {e}")

    # Test routers
    try:
        from backend.app.routers import slabs, admin, kiosk, jobs, workers
        print("[OK] backend.app.routers")
    except ImportError as e:
        errors.append(f"[FAIL] backend.app.routers: {e}")

    # Test services
    try:
        from backend.app.services import WatchFolderService, ImportProcessor
        print("[OK] backend.app.services")
    except ImportError as e:
        errors.append(f"[FAIL] backend.app.services: {e}")

    # Test utils
    try:
        from backend.app.utils import validate_image, generate_qr_code
        print("[OK] backend.app.utils")
    except ImportError as e:
        errors.append(f"[FAIL] backend.app.utils: {e}")

    # Test core
    try:
        from backend.app.core import resolve_path, log_path_map
        print("[OK] backend.app.core")
    except ImportError as e:
        errors.append(f"[FAIL] backend.app.core: {e}")

    # Test config
    try:
        from backend.app.config import settings, get_settings
        print("[OK] backend.app.config")
    except ImportError as e:
        errors.append(f"[FAIL] backend.app.config: {e}")

    # Test version
    try:
        from backend.app.version import __version__
        print(f"[OK] backend.app.version (v{__version__})")
    except ImportError as e:
        errors.append(f"[FAIL] backend.app.version: {e}")

    return errors


def main():
    """Run import smoke tests."""
    print("=" * 50)
    print("SlabHub Import Smoke Test")
    print("=" * 50)
    print()

    errors = test_imports()

    print()
    print("=" * 50)

    if errors:
        print(f"FAILED: {len(errors)} import error(s)")
        print()
        for error in errors:
            print(f"  {error}")
        sys.exit(1)
    else:
        print("PASSED: All imports successful")
        sys.exit(0)


if __name__ == "__main__":
    main()
