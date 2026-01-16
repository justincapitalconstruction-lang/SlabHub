#!/usr/bin/env python3
"""
Path Normalization Script

Normalizes existing file paths in the database to use logical paths.
Converts absolute paths to logical paths relative to SlabHub root.

Phase 2 Implementation - Normalize existing paths
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings
from backend.app.models import Slab, init_db, SessionLocal
from core import path_manager, normalize_path_for_storage


def normalize_slab_paths():
    """Normalize all file paths in slab records."""
    print("🔄 Normalizing existing slab paths...")

    db = SessionLocal()
    try:
        slabs = db.query(Slab).all()
        updated_count = 0

        for slab in slabs:
            changes = {}

            # Normalize primary image
            if slab.primary_image:
                try:
                    normalized = normalize_path_for_storage(Path(slab.primary_image))
                    if normalized != slab.primary_image:
                        changes['primary_image'] = normalized
                        print(f"  {slab.public_id}: primary_image {slab.primary_image} -> {normalized}")
                except Exception as e:
                    print(f"  ⚠️  Failed to normalize primary_image for {slab.public_id}: {e}")

            # Normalize additional images
            if slab.additional_images:
                normalized_additional = []
                for img_path in slab.additional_images:
                    try:
                        normalized = normalize_path_for_storage(Path(img_path))
                        normalized_additional.append(normalized)
                        if normalized != img_path:
                            print(f"  {slab.public_id}: additional {img_path} -> {normalized}")
                    except Exception as e:
                        print(f"  ⚠️  Failed to normalize additional image {img_path}: {e}")
                        normalized_additional.append(img_path)  # Keep original

                if normalized_additional != slab.additional_images:
                    changes['additional_images'] = normalized_additional

            # Normalize QR code path
            if slab.qr_code_path:
                try:
                    normalized = normalize_path_for_storage(Path(slab.qr_code_path))
                    if normalized != slab.qr_code_path:
                        changes['qr_code_path'] = normalized
                        print(f"  {slab.public_id}: qr_code_path {slab.qr_code_path} -> {normalized}")
                except Exception as e:
                    print(f"  ⚠️  Failed to normalize qr_code_path for {slab.public_id}: {e}")

            # Apply changes
            if changes:
                for field, value in changes.items():
                    setattr(slab, field, value)
                updated_count += 1

        db.commit()
        print(f"✅ Normalized paths for {updated_count} slabs")

    except Exception as e:
        print(f"❌ Error normalizing paths: {e}")
        db.rollback()
    finally:
        db.close()


def validate_normalized_paths():
    """Validate that all paths are now logical."""
    print("🔍 Validating normalized paths...")

    db = SessionLocal()
    try:
        slabs = db.query(Slab).all()
        violations = []

        for slab in slabs:
            # Check primary image
            if slab.primary_image and Path(slab.primary_image).is_absolute():
                violations.append(f"{slab.public_id}: absolute primary_image {slab.primary_image}")

            # Check additional images
            if slab.additional_images:
                for img in slab.additional_images:
                    if Path(img).is_absolute():
                        violations.append(f"{slab.public_id}: absolute additional {img}")

            # Check QR path
            if slab.qr_code_path and Path(slab.qr_code_path).is_absolute():
                violations.append(f"{slab.public_id}: absolute qr_code_path {slab.qr_code_path}")

        if violations:
            print("❌ Found absolute path violations:")
            for v in violations:
                print(f"  {v}")
            return False
        else:
            print("✅ All paths are logical")
            return True

    except Exception as e:
        print(f"❌ Error validating paths: {e}")
        return False
    finally:
        db.close()


def main():
    """Main normalization process."""
    print("🧭 SlabHub Path Normalization")
    print("=" * 40)

    # Initialize database
    try:
        init_db()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False

    # Normalize paths
    normalize_slab_paths()

    # Validate
    if validate_normalized_paths():
        print("\n🎉 Path normalization completed successfully!")
        return True
    else:
        print("\n💥 Path normalization failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)