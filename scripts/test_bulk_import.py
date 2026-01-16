"""
Test script to bulk import slabs from D:/slabhuv1/images_final
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.models.base import SessionLocal
from app.services.bulk_upload import BulkUploadService
from app.config import settings

def main():
    # Paths
    images_folder = Path("D:/slabhuv1/images_final")
    csv_file = images_folder / "slabs_import.csv"
    static_dir = Path(settings.static_folder)

    print("=" * 80)
    print("BULK IMPORT TEST")
    print("=" * 80)
    print(f"Images folder: {images_folder}")
    print(f"CSV file: {csv_file}")
    print(f"Static dir: {static_dir}")
    print()

    # Check files exist
    if not images_folder.exists():
        print(f"ERROR: Images folder not found: {images_folder}")
        return

    if not csv_file.exists():
        print(f"ERROR: CSV file not found: {csv_file}")
        return

    # Count images
    images = list(images_folder.glob("*.png")) + list(images_folder.glob("*.jpg"))
    print(f"Found {len(images)} images")
    print()

    # Initialize service
    db = SessionLocal()
    try:
        upload_service = BulkUploadService(
            upload_dir=str(images_folder.parent),
            static_dir=str(static_dir)
        )

        print("Starting import...")
        print("-" * 80)

        # Process upload
        success_count, error_count, errors = upload_service.process_bulk_upload(
            db=db,
            images_folder=images_folder,
            csv_file=csv_file
        )

        print("-" * 80)
        print("\nIMPORT RESULTS:")
        print(f"[OK] Successfully imported: {success_count}")
        print(f"[FAIL] Failed: {error_count}")

        if errors:
            print("\nERRORS:")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")

        print("\n" + "=" * 80)
        if error_count == 0:
            print("SUCCESS: All slabs imported successfully!")
        elif success_count > 0:
            print(f"PARTIAL SUCCESS: {success_count} imported, {error_count} failed")
        else:
            print("FAILURE: No slabs were imported")
        print("=" * 80)

    except Exception as e:
        print(f"\nERROR: Import failed with exception:")
        print(f"  {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
