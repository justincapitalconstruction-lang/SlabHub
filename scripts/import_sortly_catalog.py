#!/usr/bin/env python3
"""
Import Sortly Granite Catalog into SlabHub Database

This script imports the reference granite catalog from the Sortly project,
which contains 32+ granite types with detailed identification markers,
pricing tiers, and visual descriptions.

Usage:
    python scripts/import_sortly_catalog.py
    python scripts/import_sortly_catalog.py --catalog path/to/catalog.json
    python scripts/import_sortly_catalog.py --overwrite  # Replace existing entries
"""
import sys
import json
import argparse
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.models.base import SessionLocal, init_db
from app.models.stone_catalog import StoneCatalogEntry


# Tier symbol mapping
TIER_SYMBOLS = {
    "Value": "$",
    "Premium": "$$",
    "Platinum": "$$$",
    "Ultra Rare": "$$$$"
}


def import_catalog(catalog_path: Path, overwrite: bool = False):
    """
    Import catalog from JSON file into database

    Args:
        catalog_path: Path to granite_catalog_merged.json
        overwrite: If True, delete existing entries before importing
    """
    print(f"Importing catalog from: {catalog_path}")

    # Load catalog JSON
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog_data = json.load(f)

    print(f"Catalog version: {catalog_data.get('catalog_version', 'unknown')}")
    print(f"Vendor source: {catalog_data.get('vendor_source', 'unknown')}")
    print(f"Total items: {len(catalog_data['items'])}")

    # Initialize database
    init_db()

    # Create session
    db = SessionLocal()

    try:
        # Optionally clear existing catalog
        if overwrite:
            deleted_count = db.query(StoneCatalogEntry).delete()
            db.commit()
            print(f"Deleted {deleted_count} existing catalog entries")

        # Import each item
        imported_count = 0
        skipped_count = 0
        updated_count = 0

        for item in catalog_data['items']:
            name = item['name']

            # Check if already exists
            existing = db.query(StoneCatalogEntry).filter(
                StoneCatalogEntry.name == name
            ).first()

            if existing and not overwrite:
                print(f"Skipping existing: {name}")
                skipped_count += 1
                continue

            # Extract price range
            price_range = item.get('installed_price_usd_per_sqft_range', [0, 0])
            price_min = price_range[0] if len(price_range) > 0 else 0
            price_max = price_range[1] if len(price_range) > 1 else 0

            # Create or update catalog entry
            if existing:
                # Update existing
                existing.color_group = item.get('color_group')
                existing.tier = item.get('tier')
                existing.tier_symbol = TIER_SYMBOLS.get(item.get('tier', ''), '')
                existing.price_min_per_sqft = price_min
                existing.price_max_per_sqft = price_max
                existing.visual_description = item.get('visual_description')
                existing.pattern_fingerprint = item.get('pattern_fingerprint')
                existing.must_have_markers = item.get('must_have_markers', [])
                existing.common_confusions = item.get('common_confusions', [])
                existing.keywords = item.get('keywords', [])
                existing.reference_image = item.get('reference_image')
                existing.source = f"Sortly - {catalog_data.get('catalog_version', 'v2.0')}"
                updated_count += 1
                print(f"Updated: {name}")
            else:
                # Create new entry
                entry = StoneCatalogEntry(
                    name=name,
                    stone_type="Granite",  # All items in this catalog are granite
                    color_group=item.get('color_group'),
                    tier=item.get('tier'),
                    tier_symbol=TIER_SYMBOLS.get(item.get('tier', ''), ''),
                    price_min_per_sqft=price_min,
                    price_max_per_sqft=price_max,
                    visual_description=item.get('visual_description'),
                    pattern_fingerprint=item.get('pattern_fingerprint'),
                    must_have_markers=item.get('must_have_markers', []),
                    common_confusions=item.get('common_confusions', []),
                    keywords=item.get('keywords', []),
                    reference_image=item.get('reference_image'),
                    source=f"Sortly - {catalog_data.get('catalog_version', 'v2.0')}"
                )
                db.add(entry)
                imported_count += 1
                print(f"Imported: {name} ({item.get('tier', 'N/A')} tier)")

        # Commit all changes
        db.commit()

        print("\n" + "=" * 80)
        print("IMPORT COMPLETE")
        print("=" * 80)
        print(f"Imported: {imported_count}")
        print(f"Updated: {updated_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Total in database: {db.query(StoneCatalogEntry).count()}")

        return imported_count + updated_count

    except Exception as e:
        print(f"Error during import: {e}")
        db.rollback()
        raise

    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import Sortly granite catalog into SlabHub"
    )
    parser.add_argument(
        '--catalog',
        type=str,
        default="D:/sortly_automated_upload/granite_catalog_merged.json",
        help="Path to catalog JSON file"
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help="Overwrite existing catalog entries"
    )

    args = parser.parse_args()

    catalog_path = Path(args.catalog)

    if not catalog_path.exists():
        print(f"Error: Catalog file not found: {catalog_path}")
        print("\nTried default location: D:/sortly_automated_upload/granite_catalog_merged.json")
        print("Use --catalog to specify a different path")
        sys.exit(1)

    # Run import
    import_catalog(catalog_path, overwrite=args.overwrite)


if __name__ == "__main__":
    main()
