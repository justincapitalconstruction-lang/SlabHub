"""
Clean up broken slab entries that point to non-existent images
This will remove slabs with image paths like ./data/images/... that don't exist
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.slab import Slab

def cleanup_broken_slabs(dry_run=True):
    """Remove slabs with non-existent image paths"""

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Find slabs with broken image paths
        broken_slabs = db.query(Slab).filter(
            Slab.primary_image.like('./data/%')
        ).all()

        print(f"Found {len(broken_slabs)} slabs with broken image paths")

        if dry_run:
            print("\n=== DRY RUN MODE - No changes will be made ===")
            print("\nSlabs that would be deleted:")
            for slab in broken_slabs[:10]:  # Show first 10
                print(f"  ID: {slab.id}, Public ID: {slab.public_id}, Name: {slab.name}")
                print(f"    Image: {slab.primary_image}")

            if len(broken_slabs) > 10:
                print(f"  ... and {len(broken_slabs) - 10} more")

            print(f"\nTo actually delete these slabs, run: python scripts/cleanup_broken_slabs.py --execute")
        else:
            print("\n=== EXECUTING CLEANUP ===")

            # Delete broken slabs
            deleted_count = 0
            for slab in broken_slabs:
                db.delete(slab)
                deleted_count += 1

            db.commit()
            print(f"\n✅ Successfully deleted {deleted_count} broken slabs")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Clean up broken slab entries')
    parser.add_argument('--execute', action='store_true',
                       help='Actually delete the broken slabs (default is dry-run)')

    args = parser.parse_args()

    cleanup_broken_slabs(dry_run=not args.execute)
