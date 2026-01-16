"""
CLI script for analyzing slabs using GPT-4 Vision API

Usage:
    python scripts/analyze_slabs.py --all                    # Analyze all slabs
    python scripts/analyze_slabs.py --unlabeled              # Only unlabeled slabs
    python scripts/analyze_slabs.py --features-missing       # Only slabs without features
    python scripts/analyze_slabs.py --stone-type-missing     # Only slabs without stone type
    python scripts/analyze_slabs.py --batch BATCH_ID         # Analyze specific import batch
    python scripts/analyze_slabs.py --date-from 2026-01-01   # Slabs created after date
    python scripts/analyze_slabs.py --ids 1,2,3              # Analyze specific slab IDs
    python scripts/analyze_slabs.py --unlabeled --limit 10   # Analyze first 10 unlabeled
    python scripts/analyze_slabs.py --all --overwrite        # Re-analyze all (overwrite existing)
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from app.services.slab_analyzer import analyze_slabs_cli


def parse_date(date_str: str) -> datetime:
    """Parse date string in various formats"""
    for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze slab images using GPT-4 Vision API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Selection criteria (mutually exclusive)
    criteria = parser.add_mutually_exclusive_group(required=True)
    criteria.add_argument(
        "--all",
        action="store_true",
        help="Analyze all slabs in the database"
    )
    criteria.add_argument(
        "--unlabeled",
        action="store_true",
        help="Analyze only slabs missing features or stone type"
    )
    criteria.add_argument(
        "--features-missing",
        action="store_true",
        help="Analyze only slabs without features"
    )
    criteria.add_argument(
        "--stone-type-missing",
        action="store_true",
        help="Analyze only slabs without stone type"
    )
    criteria.add_argument(
        "--batch",
        type=str,
        metavar="BATCH_ID",
        help="Analyze slabs from specific import batch"
    )
    criteria.add_argument(
        "--ids",
        type=str,
        metavar="ID1,ID2,ID3",
        help="Analyze specific slab IDs (comma-separated)"
    )

    # Date range filters (can be combined with other criteria)
    parser.add_argument(
        "--date-from",
        type=str,
        metavar="YYYY-MM-DD",
        help="Analyze slabs created on or after this date"
    )
    parser.add_argument(
        "--date-to",
        type=str,
        metavar="YYYY-MM-DD",
        help="Analyze slabs created on or before this date"
    )

    # Options
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing values (default: only fill empty fields)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Limit analysis to first N slabs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be analyzed without making changes"
    )

    args = parser.parse_args()

    # Determine criteria
    if args.all:
        criteria_name = "all"
        kwargs = {}
    elif args.unlabeled:
        criteria_name = "unlabeled"
        kwargs = {}
    elif args.features_missing:
        criteria_name = "features_missing"
        kwargs = {}
    elif args.stone_type_missing:
        criteria_name = "stone_type_missing"
        kwargs = {}
    elif args.batch:
        criteria_name = "by_batch"
        kwargs = {"batch_id": args.batch}
    elif args.ids:
        criteria_name = "manual"
        kwargs = {"slab_ids": [int(x.strip()) for x in args.ids.split(",")]}
    else:
        parser.error("No selection criteria specified")

    # Add date filters if provided
    if args.date_from:
        kwargs["date_from"] = parse_date(args.date_from)
    if args.date_to:
        kwargs["date_to"] = parse_date(args.date_to)

    # Dry run check
    if args.dry_run:
        from app.models.base import SessionLocal
        from app.services.slab_analyzer import SlabAnalyzer

        db = SessionLocal()
        try:
            analyzer = SlabAnalyzer(require_api_key=False)
            slab_ids = analyzer.get_slabs_for_analysis(db, criteria_name, **kwargs)

            if args.limit:
                slab_ids = slab_ids[:args.limit]

            print("=" * 80)
            print("DRY RUN - No changes will be made")
            print("=" * 80)
            print(f"Criteria: {criteria_name}")
            print(f"Parameters: {kwargs}")
            print(f"Overwrite existing: {args.overwrite}")
            print(f"Limit: {args.limit or 'None'}")
            print(f"\nSlabs to analyze: {len(slab_ids)}")

            if slab_ids and len(slab_ids) <= 20:
                print("\nSlab IDs:")
                for slab_id in slab_ids:
                    slab = db.query(Slab).filter(Slab.id == slab_id).first()
                    print(f"  - ID {slab_id}: {slab.public_id} - {slab.name}")
            elif slab_ids:
                print(f"\nFirst 10 slab IDs: {slab_ids[:10]}")
                print(f"... and {len(slab_ids) - 10} more")

            print("\nRun without --dry-run to proceed with analysis")
        finally:
            db.close()
        return

    # Run analysis
    print("=" * 80)
    print("GPT-4 SLAB ANALYSIS")
    print("=" * 80)
    print(f"Criteria: {criteria_name}")
    print(f"Overwrite existing: {args.overwrite}")
    print(f"Limit: {args.limit or 'None'}")
    print("")

    try:
        analyze_slabs_cli(
            criteria=criteria_name,
            overwrite=args.overwrite,
            limit=args.limit,
            **kwargs
        )
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Import here to show import errors only when running
    from app.models.slab import Slab
    main()
