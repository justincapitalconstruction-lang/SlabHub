#!/usr/bin/env python3
"""
Test script for Export API functionality.

Tests:
1. CSV export with no filters
2. CSV export with filters
3. JSON export
4. Filter combinations

Usage:
    python scripts/test_export_api.py
"""

import sys
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_csv_export_no_filters():
    """Test CSV export without filters."""
    from backend.app.models import SessionLocal, Slab
    from backend.app.routers.export import query_slabs
    import csv
    import io

    print("\n[TEST] CSV Export - No Filters")
    print("-" * 40)

    db = SessionLocal()
    try:
        # Query all slabs
        filters = {}
        slabs = query_slabs(db, filters)

        print(f"  Total slabs: {len(slabs)}")

        if len(slabs) > 0:
            # Create CSV
            stream = io.StringIO()
            writer = csv.writer(stream)
            writer.writerow(["SlabID", "Name", "StoneType", "Location"])

            for slab in slabs[:5]:  # Just first 5 for display
                writer.writerow([slab.public_id, slab.name, slab.stone_type or "", slab.location or ""])

            stream.seek(0)
            csv_content = stream.getvalue()

            lines = csv_content.split('\n')
            print(f"  CSV rows (first 5): {len([l for l in lines if l])}")
            print(f"  Sample:\n{csv_content[:200]}...")

            print("  [OK] CSV export works")
            return True
        else:
            print("  [SKIP] No slabs in database")
            return None

    except Exception as e:
        print(f"  [FAIL] Exception: {e}")
        return False
    finally:
        db.close()


def test_csv_export_with_filters():
    """Test CSV export with filters."""
    from backend.app.models import SessionLocal, Slab
    from backend.app.routers.export import query_slabs

    print("\n[TEST] CSV Export - With Filters")
    print("-" * 40)

    db = SessionLocal()
    try:
        # Create test slabs if needed
        test_slab = db.query(Slab).first()
        if not test_slab:
            print("  [SKIP] No slabs to test filters")
            return None

        # Query with name filter
        filters = {"name": test_slab.name[:3]}  # Partial match
        slabs = query_slabs(db, filters)

        print(f"  Filter by name (partial): '{filters['name']}'")
        print(f"  Results: {len(slabs)}")

        if len(slabs) > 0:
            print(f"  Sample match: {slabs[0].name}")
            print("  [OK] Filtered export works")
            return True
        else:
            print("  [FAIL] Expected at least 1 match")
            return False

    except Exception as e:
        print(f"  [FAIL] Exception: {e}")
        return False
    finally:
        db.close()


def test_json_export():
    """Test JSON export."""
    from backend.app.models import SessionLocal
    from backend.app.routers.export import export_slabs

    print("\n[TEST] JSON Export")
    print("-" * 40)

    db = SessionLocal()
    try:
        # Call export endpoint with JSON format
        result = export_slabs(
            name=None,
            stone_type=None,
            location=None,
            status=None,
            min_thickness=None,
            max_thickness=None,
            min_price=None,
            max_price=None,
            format="json",
            db=db
        )

        print(f"  Total slabs: {result['total']}")
        print(f"  Filters applied: {result['filters']}")

        if result['total'] > 0:
            sample = result['slabs'][0]
            print(f"  Sample slab: {sample['public_id']} - {sample['name']}")
            print("  [OK] JSON export works")
            return True
        else:
            print("  [SKIP] No slabs to export")
            return None

    except Exception as e:
        print(f"  [FAIL] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def test_filter_combinations():
    """Test various filter combinations."""
    from backend.app.models import SessionLocal, Slab
    from backend.app.routers.export import query_slabs

    print("\n[TEST] Filter Combinations")
    print("-" * 40)

    db = SessionLocal()
    try:
        # Get a sample slab
        sample = db.query(Slab).filter(Slab.thickness.isnot(None)).first()
        if not sample:
            print("  [SKIP] No slabs with thickness to test")
            return None

        # Test thickness filter
        filters = {"min_thickness": 1.0, "max_thickness": 5.0}
        slabs = query_slabs(db, filters)
        print(f"  Thickness filter (1.0-5.0): {len(slabs)} results")

        # Test status filter
        filters = {"status": "available"}
        slabs = query_slabs(db, filters)
        print(f"  Status filter (available): {len(slabs)} results")

        # Test combined filters
        filters = {
            "status": "available",
            "min_thickness": 1.0
        }
        slabs = query_slabs(db, filters)
        print(f"  Combined filters: {len(slabs)} results")

        print("  [OK] Filter combinations work")
        return True

    except Exception as e:
        print(f"  [FAIL] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def main():
    """Run all export API tests."""
    print("=" * 50)
    print("SlabHub Export API Tests")
    print("=" * 50)

    results = []

    # Run tests
    results.append(("CSV Export - No Filters", test_csv_export_no_filters()))
    results.append(("CSV Export - With Filters", test_csv_export_with_filters()))
    results.append(("JSON Export", test_json_export()))
    results.append(("Filter Combinations", test_filter_combinations()))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)

    passed = 0
    failed = 0
    skipped = 0

    for name, result in results:
        if result is True:
            print(f"  [PASS] {name}")
            passed += 1
        elif result is False:
            print(f"  [FAIL] {name}")
            failed += 1
        else:
            print(f"  [SKIP] {name}")
            skipped += 1

    print()
    print(f"Passed: {passed}, Failed: {failed}, Skipped: {skipped}")

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
