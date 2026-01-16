#!/usr/bin/env python3
"""
Database Sanity Check Script

Performs comprehensive database integrity checks including:
- Foreign key consistency
- Orphaned records detection
- Absolute path detection in path fields
- Duplicate public_id detection
- Missing required fields

Returns exit code 0 if clean, 1 if issues found.

SlabHub v1.12
"""

import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import load_version
from backend.app.models import (
    Base, SessionLocal, init_db,
    Slab, InventoryItem, Shipment, ImportLog,
    AnalysisRun, AnalysisResult, AnalysisDiff,
    Job, JobEvent
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SanityCheckReport:
    """Collects and formats sanity check results."""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.checks_passed: int = 0
        self.checks_failed: int = 0
        self.start_time: datetime = datetime.now()
        self.end_time: datetime | None = None

    def add_issue(self, category: str, description: str, details: Dict[str, Any] = None):
        """Add an issue to the report."""
        self.issues.append({
            "category": category,
            "description": description,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })
        self.checks_failed += 1

    def add_warning(self, category: str, description: str, details: Dict[str, Any] = None):
        """Add a warning to the report."""
        self.warnings.append({
            "category": category,
            "description": description,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        })

    def check_passed(self):
        """Mark a check as passed."""
        self.checks_passed += 1

    def finalize(self):
        """Finalize the report."""
        self.end_time = datetime.now()

    def is_clean(self) -> bool:
        """Return True if no issues found."""
        return len(self.issues) == 0

    def print_report(self):
        """Print formatted report to stdout."""
        self.finalize()
        duration = (self.end_time - self.start_time).total_seconds()

        print("\n" + "=" * 60)
        print("DATABASE SANITY CHECK REPORT")
        print("=" * 60)
        print(f"Start time: {self.start_time.isoformat()}")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Checks passed: {self.checks_passed}")
        print(f"Checks failed: {self.checks_failed}")
        print(f"Warnings: {len(self.warnings)}")
        print()

        if self.issues:
            print("-" * 60)
            print("ISSUES FOUND:")
            print("-" * 60)
            for i, issue in enumerate(self.issues, 1):
                print(f"\n{i}. [{issue['category']}] {issue['description']}")
                if issue['details']:
                    for key, value in issue['details'].items():
                        if isinstance(value, list) and len(value) > 5:
                            print(f"   {key}: {value[:5]} ... (and {len(value) - 5} more)")
                        else:
                            print(f"   {key}: {value}")

        if self.warnings:
            print("\n" + "-" * 60)
            print("WARNINGS:")
            print("-" * 60)
            for i, warning in enumerate(self.warnings, 1):
                print(f"\n{i}. [{warning['category']}] {warning['description']}")
                if warning['details']:
                    for key, value in warning['details'].items():
                        if isinstance(value, list) and len(value) > 5:
                            print(f"   {key}: {value[:5]} ... (and {len(value) - 5} more)")
                        else:
                            print(f"   {key}: {value}")

        print("\n" + "=" * 60)
        if self.is_clean():
            print("RESULT: CLEAN - No issues found")
        else:
            print(f"RESULT: ISSUES FOUND - {len(self.issues)} issue(s) detected")
        print("=" * 60 + "\n")


def check_foreign_keys(db, report: SanityCheckReport) -> None:
    """Check that all foreign keys point to valid records."""
    logger.info("Checking foreign key consistency...")

    # Check AnalysisResult -> AnalysisRun
    orphaned_results = db.query(AnalysisResult).filter(
        ~AnalysisResult.run_id.in_(db.query(AnalysisRun.id))
    ).all()
    if orphaned_results:
        report.add_issue(
            "FK_INTEGRITY",
            f"AnalysisResult records with invalid run_id",
            {"count": len(orphaned_results), "ids": [r.id for r in orphaned_results[:10]]}
        )
    else:
        report.check_passed()

    # Check AnalysisResult -> Slab (nullable FK)
    invalid_slab_refs = db.query(AnalysisResult).filter(
        AnalysisResult.slab_id.isnot(None),
        ~AnalysisResult.slab_id.in_(db.query(Slab.id))
    ).all()
    if invalid_slab_refs:
        report.add_warning(
            "FK_INTEGRITY",
            f"AnalysisResult records with invalid slab_id (SET NULL expected)",
            {"count": len(invalid_slab_refs), "ids": [r.id for r in invalid_slab_refs[:10]]}
        )
    else:
        report.check_passed()

    # Check AnalysisDiff -> AnalysisRun
    orphaned_diffs = db.query(AnalysisDiff).filter(
        ~AnalysisDiff.run_id.in_(db.query(AnalysisRun.id))
    ).all()
    if orphaned_diffs:
        report.add_issue(
            "FK_INTEGRITY",
            f"AnalysisDiff records with invalid run_id",
            {"count": len(orphaned_diffs), "ids": [d.id for d in orphaned_diffs[:10]]}
        )
    else:
        report.check_passed()

    # Check AnalysisDiff -> Slab
    invalid_diff_slabs = db.query(AnalysisDiff).filter(
        ~AnalysisDiff.slab_id.in_(db.query(Slab.id))
    ).all()
    if invalid_diff_slabs:
        report.add_issue(
            "FK_INTEGRITY",
            f"AnalysisDiff records with invalid slab_id",
            {"count": len(invalid_diff_slabs), "ids": [d.id for d in invalid_diff_slabs[:10]]}
        )
    else:
        report.check_passed()

    # Check JobEvent -> Job
    orphaned_events = db.query(JobEvent).filter(
        ~JobEvent.job_id.in_(db.query(Job.id))
    ).all()
    if orphaned_events:
        report.add_issue(
            "FK_INTEGRITY",
            f"JobEvent records with invalid job_id",
            {"count": len(orphaned_events), "ids": [e.id for e in orphaned_events[:10]]}
        )
    else:
        report.check_passed()


def check_orphaned_records(db, report: SanityCheckReport) -> None:
    """Check for orphaned records that may need cleanup."""
    logger.info("Checking for orphaned records...")

    # Check for slabs with import_batch_id not in import_logs
    slabs_with_batch = db.query(Slab).filter(Slab.import_batch_id.isnot(None)).all()
    known_batches = {log.batch_id for log in db.query(ImportLog).all()}

    orphaned_batches = []
    for slab in slabs_with_batch:
        if slab.import_batch_id not in known_batches:
            orphaned_batches.append(slab.public_id)

    if orphaned_batches:
        report.add_warning(
            "ORPHANED_RECORDS",
            f"Slabs with import_batch_id not found in import_logs",
            {"count": len(orphaned_batches), "slab_ids": orphaned_batches[:10]}
        )
    else:
        report.check_passed()

    # Check for AnalysisRun with no results
    runs_without_results = db.query(AnalysisRun).filter(
        ~AnalysisRun.id.in_(db.query(AnalysisResult.run_id).distinct())
    ).all()
    if runs_without_results:
        report.add_warning(
            "ORPHANED_RECORDS",
            f"AnalysisRun records with no results",
            {"count": len(runs_without_results), "run_ids": [r.id for r in runs_without_results[:10]]}
        )
    else:
        report.check_passed()


def check_absolute_paths(db, report: SanityCheckReport) -> None:
    """Check for absolute paths in path fields (should be logical paths)."""
    logger.info("Checking for absolute paths...")

    absolute_paths_found = []

    # Check Slab path fields
    slabs = db.query(Slab).all()
    for slab in slabs:
        # Check primary_image
        if slab.primary_image and Path(slab.primary_image).is_absolute():
            absolute_paths_found.append({
                "table": "slabs",
                "id": slab.id,
                "public_id": slab.public_id,
                "field": "primary_image",
                "value": slab.primary_image
            })

        # Check additional_images (JSON array)
        if slab.additional_images:
            for i, img_path in enumerate(slab.additional_images):
                if img_path and Path(img_path).is_absolute():
                    absolute_paths_found.append({
                        "table": "slabs",
                        "id": slab.id,
                        "public_id": slab.public_id,
                        "field": f"additional_images[{i}]",
                        "value": img_path
                    })

        # Check qr_code_path
        if slab.qr_code_path and Path(slab.qr_code_path).is_absolute():
            absolute_paths_found.append({
                "table": "slabs",
                "id": slab.id,
                "public_id": slab.public_id,
                "field": "qr_code_path",
                "value": slab.qr_code_path
            })

    # Check ImportLog source_path
    import_logs = db.query(ImportLog).all()
    for log in import_logs:
        if log.source_path and Path(log.source_path).is_absolute():
            absolute_paths_found.append({
                "table": "import_logs",
                "id": log.id,
                "batch_id": log.batch_id,
                "field": "source_path",
                "value": log.source_path
            })

    if absolute_paths_found:
        report.add_issue(
            "ABSOLUTE_PATHS",
            f"Found {len(absolute_paths_found)} absolute path(s) in database",
            {"paths": absolute_paths_found[:20]}
        )
    else:
        report.check_passed()


def check_duplicate_public_ids(db, report: SanityCheckReport) -> None:
    """Check for duplicate public_ids in slabs table."""
    logger.info("Checking for duplicate public_ids...")

    from sqlalchemy import func

    # Find duplicate public_ids
    duplicates = db.query(
        Slab.public_id, func.count(Slab.id).label('count')
    ).group_by(Slab.public_id).having(func.count(Slab.id) > 1).all()

    if duplicates:
        dup_details = [{"public_id": d.public_id, "count": d.count} for d in duplicates]
        report.add_issue(
            "DUPLICATE_PUBLIC_ID",
            f"Found {len(duplicates)} duplicate public_id(s)",
            {"duplicates": dup_details}
        )
    else:
        report.check_passed()


def check_required_fields(db, report: SanityCheckReport) -> None:
    """Check for missing required fields."""
    logger.info("Checking for missing required fields...")

    # Slabs - name and public_id are required
    slabs_missing_name = db.query(Slab).filter(
        (Slab.name.is_(None)) | (Slab.name == "")
    ).all()
    if slabs_missing_name:
        report.add_issue(
            "MISSING_REQUIRED",
            f"Slabs with missing or empty name",
            {"count": len(slabs_missing_name), "ids": [s.id for s in slabs_missing_name[:10]]}
        )
    else:
        report.check_passed()

    slabs_missing_public_id = db.query(Slab).filter(
        (Slab.public_id.is_(None)) | (Slab.public_id == "")
    ).all()
    if slabs_missing_public_id:
        report.add_issue(
            "MISSING_REQUIRED",
            f"Slabs with missing or empty public_id",
            {"count": len(slabs_missing_public_id), "ids": [s.id for s in slabs_missing_public_id[:10]]}
        )
    else:
        report.check_passed()

    # InventoryItem - sku and name are required
    items_missing_sku = db.query(InventoryItem).filter(
        (InventoryItem.sku.is_(None)) | (InventoryItem.sku == "")
    ).all()
    if items_missing_sku:
        report.add_issue(
            "MISSING_REQUIRED",
            f"InventoryItems with missing or empty sku",
            {"count": len(items_missing_sku), "ids": [i.id for i in items_missing_sku[:10]]}
        )
    else:
        report.check_passed()

    items_missing_name = db.query(InventoryItem).filter(
        (InventoryItem.name.is_(None)) | (InventoryItem.name == "")
    ).all()
    if items_missing_name:
        report.add_issue(
            "MISSING_REQUIRED",
            f"InventoryItems with missing or empty name",
            {"count": len(items_missing_name), "ids": [i.id for i in items_missing_name[:10]]}
        )
    else:
        report.check_passed()

    # Shipment - supplier is required
    shipments_missing_supplier = db.query(Shipment).filter(
        (Shipment.supplier.is_(None)) | (Shipment.supplier == "")
    ).all()
    if shipments_missing_supplier:
        report.add_issue(
            "MISSING_REQUIRED",
            f"Shipments with missing or empty supplier",
            {"count": len(shipments_missing_supplier), "ids": [s.id for s in shipments_missing_supplier[:10]]}
        )
    else:
        report.check_passed()

    # ImportLog - batch_id and import_type are required
    logs_missing_batch = db.query(ImportLog).filter(
        (ImportLog.batch_id.is_(None)) | (ImportLog.batch_id == "")
    ).all()
    if logs_missing_batch:
        report.add_issue(
            "MISSING_REQUIRED",
            f"ImportLogs with missing or empty batch_id",
            {"count": len(logs_missing_batch), "ids": [l.id for l in logs_missing_batch[:10]]}
        )
    else:
        report.check_passed()

    # Job - job_id and job_type are required
    jobs_missing_id = db.query(Job).filter(
        (Job.job_id.is_(None)) | (Job.job_id == "")
    ).all()
    if jobs_missing_id:
        report.add_issue(
            "MISSING_REQUIRED",
            f"Jobs with missing or empty job_id",
            {"count": len(jobs_missing_id), "ids": [j.id for j in jobs_missing_id[:10]]}
        )
    else:
        report.check_passed()


def check_data_consistency(db, report: SanityCheckReport) -> None:
    """Check for logical data consistency issues."""
    logger.info("Checking data consistency...")

    # Check for slabs with negative quantities
    negative_qty_slabs = db.query(Slab).filter(Slab.quantity < 0).all()
    if negative_qty_slabs:
        report.add_issue(
            "DATA_CONSISTENCY",
            f"Slabs with negative quantity",
            {"count": len(negative_qty_slabs), "ids": [s.public_id for s in negative_qty_slabs[:10]]}
        )
    else:
        report.check_passed()

    # Check for inventory items with negative quantities
    negative_qty_items = db.query(InventoryItem).filter(InventoryItem.qty_on_hand < 0).all()
    if negative_qty_items:
        report.add_issue(
            "DATA_CONSISTENCY",
            f"InventoryItems with negative qty_on_hand",
            {"count": len(negative_qty_items), "ids": [i.sku for i in negative_qty_items[:10]]}
        )
    else:
        report.check_passed()

    # Check for completed imports with 0 items processed
    empty_imports = db.query(ImportLog).filter(
        ImportLog.status == "completed",
        ImportLog.items_processed == 0
    ).all()
    if empty_imports:
        report.add_warning(
            "DATA_CONSISTENCY",
            f"Completed imports with 0 items processed",
            {"count": len(empty_imports), "batch_ids": [i.batch_id for i in empty_imports[:10]]}
        )
    else:
        report.check_passed()


def run_sanity_check(verbose: bool = False) -> Tuple[SanityCheckReport, bool]:
    """Run all sanity checks and return report."""
    report = SanityCheckReport()

    try:
        # Initialize database connection
        init_db()
        db = SessionLocal()

        try:
            # Run all checks
            check_foreign_keys(db, report)
            check_orphaned_records(db, report)
            check_absolute_paths(db, report)
            check_duplicate_public_ids(db, report)
            check_required_fields(db, report)
            check_data_consistency(db, report)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error during sanity check: {e}")
        report.add_issue(
            "SYSTEM_ERROR",
            f"Error during sanity check: {str(e)}",
            {"exception_type": type(e).__name__}
        )

    return report, report.is_clean()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database Sanity Check for SlabHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python db_sanity_check.py              Run all checks
  python db_sanity_check.py --verbose    Run with verbose output
  python db_sanity_check.py --json       Output as JSON
        """
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"SlabHub Database Sanity Check v{load_version()}"
    )

    args = parser.parse_args()

    # Print version on startup
    version = load_version()
    print(f"SlabHub Database Sanity Check v{version}")
    print("-" * 40)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run checks
    report, is_clean = run_sanity_check(verbose=args.verbose)

    # Output results
    if args.json:
        import json
        output = {
            "version": version,
            "start_time": report.start_time.isoformat(),
            "end_time": report.end_time.isoformat() if report.end_time else None,
            "checks_passed": report.checks_passed,
            "checks_failed": report.checks_failed,
            "is_clean": is_clean,
            "issues": report.issues,
            "warnings": report.warnings
        }
        print(json.dumps(output, indent=2))
    else:
        report.print_report()

    # Return appropriate exit code
    sys.exit(0 if is_clean else 1)


if __name__ == "__main__":
    main()
