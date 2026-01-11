#!/usr/bin/env python3
"""
Initialize SlabHub database
Creates all tables if they don't exist
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.models import init_db

if __name__ == '__main__':
    print("Initializing database...")
    init_db()
    print("Database initialized successfully!")
