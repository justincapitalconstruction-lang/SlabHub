"""
Test script for GPT analysis functionality
Tests the analysis service without making actual API calls
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.models.base import SessionLocal
from app.models.slab import Slab


def test_selection_criteria():
    """Test different selection criteria"""
    print("=" * 80)
    print("GPT ANALYSIS - SELECTION CRITERIA TEST")
    print("=" * 80)

    db = SessionLocal()
    try:
        # Import here to avoid import errors if openai not installed
        try:
            from app.services.slab_analyzer import SlabAnalyzer
            print("[OK] SlabAnalyzer imported successfully")
        except ImportError as e:
            print(f"[FAIL] Failed to import SlabAnalyzer: {e}")
            print("\nNote: This is expected if OPENAI_API_KEY is not set in .env")
            print("To fix: Add OPENAI_API_KEY=your-key-here to .env file")
            return

        # Create analyzer (will fail if no API key, which is OK for testing)
        try:
            analyzer = SlabAnalyzer()
            has_api_key = True
            print("[OK] SlabAnalyzer initialized")
        except ValueError as e:
            print(f"[INFO] No API key configured (expected): {e}")
            has_api_key = False
            # Create a mock for testing selection logic
            class MockAnalyzer:
                def get_slabs_for_analysis(self, *args, **kwargs):
                    from app.services.slab_analyzer import SlabAnalyzer
                    temp = object.__new__(SlabAnalyzer)
                    return temp.get_slabs_for_analysis(*args, **kwargs)
            analyzer = MockAnalyzer()

        # Test 1: All slabs
        print("\nTest 1: All slabs")
        slab_ids = analyzer.get_slabs_for_analysis(db, "all")
        print(f"  Found {len(slab_ids)} slabs total")

        # Test 2: Unlabeled slabs
        print("\nTest 2: Unlabeled slabs")
        slab_ids = analyzer.get_slabs_for_analysis(db, "unlabeled")
        print(f"  Found {len(slab_ids)} unlabeled slabs")

        # Test 3: Features missing
        print("\nTest 3: Features missing")
        slab_ids = analyzer.get_slabs_for_analysis(db, "features_missing")
        print(f"  Found {len(slab_ids)} slabs without features")

        # Test 4: Stone type missing
        print("\nTest 4: Stone type missing")
        slab_ids = analyzer.get_slabs_for_analysis(db, "stone_type_missing")
        print(f"  Found {len(slab_ids)} slabs without stone type")

        # Test 5: Manual selection
        print("\nTest 5: Manual selection")
        if slab_ids:
            test_ids = slab_ids[:3]  # First 3 from previous query
            selected = analyzer.get_slabs_for_analysis(db, "manual", slab_ids=test_ids)
            print(f"  Selected {len(selected)} slabs manually: {selected}")

        # Show sample unlabeled slabs
        print("\n" + "=" * 80)
        print("SAMPLE UNLABELED SLABS")
        print("=" * 80)

        unlabeled = db.query(Slab).filter(
            ((Slab.features == None) | (Slab.features == "")) |
            ((Slab.stone_type == None) | (Slab.stone_type == ""))
        ).filter(
            Slab.primary_image != None
        ).limit(10).all()

        if unlabeled:
            print(f"\nShowing first {len(unlabeled)} unlabeled slabs:\n")
            for slab in unlabeled:
                features = slab.features or "(empty)"
                stone_type = slab.stone_type or "(empty)"
                print(f"  ID {slab.id}: {slab.public_id} - {slab.name}")
                print(f"    Stone Type: {stone_type}")
                print(f"    Features: {features}")
                print(f"    Image: {slab.primary_image or '(none)'}")
                print()
        else:
            print("\n  No unlabeled slabs found - all slabs have labels!")

        # Summary
        print("=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total = db.query(Slab).count()
        with_images = db.query(Slab).filter(Slab.primary_image != None).count()
        unlabeled_count = db.query(Slab).filter(
            ((Slab.features == None) | (Slab.features == "")) |
            ((Slab.stone_type == None) | (Slab.stone_type == ""))
        ).count()

        print(f"Total slabs in database: {total}")
        print(f"Slabs with images: {with_images}")
        print(f"Unlabeled slabs: {unlabeled_count}")

        if has_api_key:
            print("\nAPI Key Status: [OK] Configured")
            print("\nReady for GPT analysis!")
            print("\nNext steps:")
            print("  1. Web UI: http://localhost:8000/admin/slab-analysis")
            print("  2. CLI: python scripts/analyze_slabs.py --unlabeled --limit 5")
        else:
            print("\nAPI Key Status: [MISSING] Not configured")
            print("\nTo enable GPT analysis:")
            print("  1. Get API key from https://platform.openai.com/")
            print("  2. Add to .env file: OPENAI_API_KEY=sk-your-key-here")
            print("  3. Restart the application")

    finally:
        db.close()


if __name__ == "__main__":
    test_selection_criteria()
