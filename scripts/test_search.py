"""
Test customer search functionality
Tests search by features, stone type, size range, and name
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.models.base import SessionLocal
from app.crud import get_slabs

def test_search(description, filters=None):
    """Test a search with given filters"""
    print(f"\nTest: {description}")
    print(f"Filters: {filters}")

    db = SessionLocal()
    try:
        slabs, total = get_slabs(db, filters=filters)
        print(f"Results: {total} slabs found")
        if total > 0:
            print("Sample results:")
            for slab in slabs[:5]:
                features = slab.features or "N/A"
                stone = slab.stone_type or "N/A"
                size = slab.square_feet or 0
                print(f"  - {slab.name} | {features} | {stone} | {size:.1f} sqft")
        return total
    finally:
        db.close()

def main():
    print("=" * 80)
    print("CUSTOMER SEARCH FUNCTIONALITY TEST")
    print("=" * 80)

    # Test 1: Search by features (keywords)
    test_search("Search for 'veins' in features", filters={"features": "veins"})

    # Test 2: Search by features (multiple keywords)
    test_search("Search for 'silver specks' in features", filters={"features": "silver specks"})

    # Test 3: Search by stone type
    test_search("Search for Granite", filters={"stone_type": "Granite"})

    # Test 4: Search by stone type (Quartzite)
    test_search("Search for Quartzite", filters={"stone_type": "Quartzite"})

    # Test 5: Search by name
    test_search("Search for 'Black' in name", filters={"search": "Black"})

    # Test 6: Search by size range (min)
    test_search("Search for slabs >= 60 sqft", filters={"min_size": 60})

    # Test 7: Search by size range (max)
    test_search("Search for slabs <= 50 sqft", filters={"max_size": 50})

    # Test 8: Search by size range (both)
    test_search("Search for slabs 55-65 sqft", filters={"min_size": 55, "max_size": 65})

    # Test 9: Combined search (features + stone type)
    test_search("Search for Granite with 'grey'", filters={"stone_type": "Granite", "features": "grey"})

    # Test 10: Combined search (name + size)
    test_search("Search for 'White' >= 55 sqft", filters={"search": "White", "min_size": 55})

    # Test 11: All filters combined
    test_search(
        "Search for Granite with 'swirls', name contains 'Grey', 50-70 sqft",
        filters={
            "stone_type": "Granite",
            "features": "swirls",
            "search": "Grey",
            "min_size": 50,
            "max_size": 70
        }
    )

    print("\n" + "=" * 80)
    print("SEARCH TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    main()
