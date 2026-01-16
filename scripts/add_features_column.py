"""
Migration script to add features column to slabs table
"""
import sqlite3
from pathlib import Path

# Get database path
db_path = Path(__file__).parent.parent / "data" / "slabhub.db"

print(f"Adding features column to: {db_path}")

# Connect to database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if column already exists
    cursor.execute("PRAGMA table_info(slabs)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'features' in columns:
        print("[OK] Features column already exists!")
    else:
        # Add the column
        cursor.execute("""
            ALTER TABLE slabs
            ADD COLUMN features VARCHAR(500)
        """)
        conn.commit()
        print("[OK] Successfully added features column!")

    # Verify
    cursor.execute("PRAGMA table_info(slabs)")
    columns = [column[1] for column in cursor.fetchall()]
    print(f"\n[INFO] Current columns in slabs table:")
    for col in columns:
        print(f"  - {col}")

except Exception as e:
    print(f"[ERROR] Failed to add column: {e}")
    conn.rollback()
finally:
    conn.close()

print("\n[SUCCESS] Migration complete!")
