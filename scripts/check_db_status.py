"""Quick database status checker"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from app.config import settings

def check_status():
    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        # Check slabs
        result = conn.execute(text("SELECT COUNT(*) as count FROM slabs"))
        slab_count = result.fetchone()[0]
        print(f"Total Slabs: {slab_count}")

        # Check import logs
        result = conn.execute(text("""
            SELECT
                import_type,
                status,
                items_processed,
                items_success,
                items_failed,
                created_at
            FROM import_logs
            ORDER BY created_at DESC
            LIMIT 10
        """))

        print("\nRecent Import Logs:")
        print("-" * 80)
        for row in result:
            print(f"{row.created_at} | {row.import_type} | Status: {row.status}")
            print(f"  Processed: {row.items_processed}, Success: {row.items_success}, Failed: {row.items_failed}")

        # Check slabs with images
        result = conn.execute(text("""
            SELECT COUNT(*) as count
            FROM slabs
            WHERE primary_image IS NOT NULL
        """))
        slabs_with_images = result.fetchone()[0]
        print(f"\nSlabs with images: {slabs_with_images}")

        # Sample some slabs
        result = conn.execute(text("""
            SELECT id, public_id, name, stone_type, primary_image
            FROM slabs
            LIMIT 5
        """))
        print("\nSample Slabs:")
        print("-" * 80)
        for row in result:
            print(f"ID: {row.id} | Public ID: {row.public_id}")
            print(f"  Name: {row.name}")
            print(f"  Type: {row.stone_type}")
            print(f"  Image: {row.primary_image}")
            print()

if __name__ == "__main__":
    check_status()
