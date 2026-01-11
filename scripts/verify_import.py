#!/usr/bin/env python3
"""
Verify import results
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.models import SessionLocal, Slab, ImportLog

if __name__ == '__main__':
    db = SessionLocal()

    # Count slabs
    slab_count = db.query(Slab).count()
    print(f"\nTotal Slabs in Database: {slab_count}")

    # Show recent slabs
    print("\nRecent Slabs:")
    print("-" * 80)
    for slab in db.query(Slab).order_by(Slab.created_at.desc()).limit(5).all():
        print(f"  [{slab.public_id}] {slab.name}")
        print(f"    Type: {slab.stone_type}, Supplier: {slab.supplier}")
        print(f"    Location: {slab.location}, Status: {slab.status}")
        if slab.tags:
            print(f"    Tags: {slab.tags}")
        if slab.extra_json:
            print(f"    Extra: {slab.extra_json}")
        print()

    # Show import logs
    import_count = db.query(ImportLog).count()
    print(f"Total Import Logs: {import_count}")
    print("\nRecent Imports:")
    print("-" * 80)
    for log in db.query(ImportLog).order_by(ImportLog.created_at.desc()).limit(3).all():
        print(f"  Batch: {log.batch_id}")
        print(f"  Type: {log.import_type}")
        print(f"  Status: {log.status}")
        print(f"  Processed: {log.items_processed}, Success: {log.items_success}, Failed: {log.items_failed}, Skipped: {log.items_skipped}")
        print(f"  Success Rate: {log.get_success_rate():.1f}%")
        print()

    db.close()
