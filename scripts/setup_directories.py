"""
Setup script to create required directories for SlabHub
Creates all necessary folders for images, QR codes, labels, etc.
"""
import os
from pathlib import Path

# Get project root
project_root = Path(__file__).parent.parent

# Define all required directories
directories = [
    # Static files
    project_root / "backend" / "app" / "static" / "images" / "slabs",
    project_root / "backend" / "app" / "static" / "qr",
    project_root / "backend" / "app" / "static" / "labels",

    # Data directories
    project_root / "data" / "qr",
    project_root / "data" / "labels",
    project_root / "data" / "logs",
    project_root / "data" / "slabcrop_inbox",
    project_root / "data" / "incoming_raw",
    project_root / "data" / "archive",
]

def setup_directories():
    """Create all required directories"""
    print("Setting up directories...")

    for directory in directories:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"[OK] Created: {directory}")
        except Exception as e:
            print(f"[FAIL] Failed to create {directory}: {e}")

    # Create a placeholder .gitkeep in each directory
    for directory in directories:
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    print("\n[SUCCESS] All directories created successfully!")
    print("\nDirectory structure:")
    print("backend/app/static/")
    print("  ├── images/slabs/  (slab images)")
    print("  ├── qr/            (QR codes)")
    print("  └── labels/        (labels)")
    print("\ndata/")
    print("  ├── qr/")
    print("  ├── labels/")
    print("  ├── logs/")
    print("  ├── slabcrop_inbox/")
    print("  ├── incoming_raw/")
    print("  └── archive/")

if __name__ == "__main__":
    setup_directories()
