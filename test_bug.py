#!/usr/bin/env python3
"""Quick test to confirm the router bug"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from app.crud import get_inventory_items
from app.models import SessionLocal

db = SessionLocal()

# Test correct usage
filters = {'search': 'test'}
items, total = get_inventory_items(db, skip=0, limit=10, filters=filters)
print(f'CORRECT: get_inventory_items with filters= works: Found {total} items')

# Test incorrect usage (as in routers)
try:
    items2, total2 = get_inventory_items(db, skip=0, limit=10, **filters)
    print(f'BUG CONFIRMED: **filters should fail but worked: Found {total2} items')
except TypeError as e:
    print(f'BUG CONFIRMED: **filters fails with TypeError: {e}')

db.close()
