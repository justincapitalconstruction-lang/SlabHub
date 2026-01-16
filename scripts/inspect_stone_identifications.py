#!/usr/bin/env python3
"""
Inspect stone-identifications.json schema quickly.

This utility script analyzes the structure of stone metadata JSON files
to understand their schema before importing. Useful for debugging import
issues and understanding data structure.

Usage:
    python scripts/inspect_stone_identifications.py --path data.json
    python scripts/inspect_stone_identifications.py --path data.json --sample 3
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Inspect stone-identifications.json schema quickly.")
    p.add_argument("--path", required=True, help="Path to stone-identifications.json")
    p.add_argument("--sample", type=int, default=1, help="How many sample entries to print")
    return p.parse_args()


def iter_entries(data: Any) -> List[Dict[str, Any]]:
    """
    Extract entries from various JSON structures.

    Handles:
    - List of dictionaries: [{"id": 1, ...}, {"id": 2, ...}]
    - Dict with 'items' key: {"items": [{"id": 1, ...}]}
    - Dict mapping id->entry: {"1": {"name": ...}, "2": {"name": ...}}

    Args:
        data: Parsed JSON data

    Returns:
        List of entry dictionaries
    """
    # Allow either list[dict], dict with 'items', or dict of id->dict
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        if "items" in data and isinstance(data["items"], list):
            return [x for x in data["items"] if isinstance(x, dict)]
        # id->entry map
        vals = [v for v in data.values() if isinstance(v, dict)]
        if vals:
            return vals
    return []


def type_name(v: Any) -> str:
    """
    Get simplified type name for a value.

    Args:
        v: Any value

    Returns:
        Simplified type name (str, num, list, dict, null)
    """
    if v is None:
        return "null"
    t = type(v).__name__
    if isinstance(v, str):
        return "str"
    if isinstance(v, (int, float)):
        return "num"
    if isinstance(v, list):
        return "list"
    if isinstance(v, dict):
        return "dict"
    return t


def main() -> None:
    args = parse_args()

    # Load JSON file
    try:
        with open(args.path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.path}")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}")
        return

    # Extract entries
    entries = iter_entries(data)
    print(f"Top-level type: {type(data).__name__}")
    print(f"Detected entries: {len(entries)}")

    if not entries:
        print("\nWarning: No entries detected in JSON file!")
        print("Expected format: list of dicts, or dict with 'items' key, or id->dict mapping")
        return

    # Analyze schema
    key_counts: Counter[str] = Counter()
    key_types: Dict[str, Counter[str]] = defaultdict(Counter)

    for e in entries:
        for k, v in e.items():
            key_counts[k] += 1
            key_types[k][type_name(v)] += 1

    # Print statistics
    print("\nMost common keys:")
    for k, c in key_counts.most_common(40):
        print(f"  {k}: {c}  types={dict(key_types[k])}")

    # Print samples
    print("\nSample entries:")
    for i in range(min(args.sample, len(entries))):
        print(f"\n--- SAMPLE {i+1} ---")
        print(json.dumps(entries[i], ensure_ascii=False, indent=2))

    # Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total entries: {len(entries)}")
    print(f"Total unique keys: {len(key_counts)}")
    print(f"Most common key: {key_counts.most_common(1)[0][0] if key_counts else 'N/A'}")


if __name__ == "__main__":
    main()
