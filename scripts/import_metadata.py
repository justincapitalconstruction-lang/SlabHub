#!/usr/bin/env python3
"""
SlabHub Metadata Importer
Standalone script to import stone slab data from stone-identifications.json

Usage:
    python scripts/import_metadata.py
    python scripts/import_metadata.py --file path/to/file.json
    python scripts/import_metadata.py --dry-run
    python scripts/import_metadata.py --file custom.json --dry-run

Features:
    - Imports from JSON (single object or array of objects)
    - Maps common field names to Slab model
    - Generates unique public IDs and QR codes
    - Calculates perceptual hashes for duplicate detection
    - Tracks imports with ImportLog
    - Progress display and summary report
    - Error handling with detailed logging
    - Dry-run mode for preview
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.models import SessionLocal, Slab, ImportLog
from backend.app.utils import (
    calculate_perceptual_hash,
    generate_short_id,
    generate_qr_code,
    is_duplicate,
)
from backend.app.config import settings


# Configure logging
def setup_logging(log_file: Optional[Path] = None) -> None:
    """Configure logging with console and file output"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if log_file is None:
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"import_metadata_{timestamp}.log"

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info(f"Logging to: {log_file}")


logger = logging.getLogger(__name__)


class FieldMapper:
    """Maps various field name variations to Slab model fields"""

    # Define field mappings: canonical_field -> list of possible variations
    FIELD_MAPPINGS = {
        'name': ['name', 'title', 'description', 'slab_name', 'identifier'],
        'stone_type': ['stone_type', 'type', 'material', 'stone', 'material_type'],
        'supplier': ['supplier', 'vendor', 'source', 'provider'],
        'finish': ['finish', 'surface', 'surface_finish', 'treatment'],
        'thickness': ['thickness', 'thick'],
        'color': ['color', 'colour', 'primary_color'],
        'dimensions': ['dimensions', 'size', 'dims'],
        'length': ['length', 'len'],
        'width': ['width', 'w'],
        'square_feet': ['square_feet', 'sqft', 'sq_ft', 'area'],
        'location': ['location', 'warehouse_location', 'storage_location', 'warehouse'],
        'status': ['status', 'state', 'availability'],
        'quantity': ['quantity', 'qty', 'count'],
        'tags': ['tags', 'categories', 'labels'],
        'notes': ['notes', 'description', 'comments', 'memo'],
        'primary_image': ['primary_image', 'image', 'image_path', 'photo', 'picture', 'main_image'],
        'additional_images': ['additional_images', 'images', 'photos', 'pictures'],
        'cost': ['cost', 'purchase_price', 'cost_price'],
        'price': ['price', 'selling_price', 'sale_price', 'retail_price'],
    }

    @classmethod
    def map_field(cls, field_name: str) -> Optional[str]:
        """Map a field name to its canonical Slab model field"""
        field_lower = field_name.lower().strip()

        for canonical, variations in cls.FIELD_MAPPINGS.items():
            if field_lower in variations:
                return canonical

        return None

    @classmethod
    def map_data(cls, data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Map input data to Slab model fields

        Returns:
            Tuple of (mapped_fields, unmapped_fields)
        """
        mapped = {}
        unmapped = {}

        for key, value in data.items():
            canonical = cls.map_field(key)

            if canonical:
                mapped[canonical] = value
            else:
                unmapped[key] = value

        return mapped, unmapped


class DimensionsParser:
    """Parse dimension strings into length and width"""

    @staticmethod
    def parse(dimensions: str) -> tuple[Optional[float], Optional[float]]:
        """
        Parse dimension string like "120x80" into (length, width)

        Supports formats:
            - "120x80"
            - "120 x 80"
            - "120X80"
            - "120 by 80"

        Returns:
            Tuple of (length, width) or (None, None) if parsing fails
        """
        if not dimensions or not isinstance(dimensions, str):
            return None, None

        # Try various patterns
        patterns = [
            r'(\d+(?:\.\d+)?)\s*[xX×]\s*(\d+(?:\.\d+)?)',  # 120x80, 120 x 80
            r'(\d+(?:\.\d+)?)\s+by\s+(\d+(?:\.\d+)?)',      # 120 by 80
        ]

        for pattern in patterns:
            match = re.search(pattern, dimensions)
            if match:
                try:
                    length = float(match.group(1))
                    width = float(match.group(2))
                    return length, width
                except ValueError:
                    continue

        return None, None


class MetadataImporter:
    """Main importer class for processing JSON metadata"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.stats = {
            'processed': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
        }
        self.errors = []
        self.warnings = []
        self.batch_id = generate_short_id(16)

    def load_json(self, file_path: Path) -> list[dict[str, Any]]:
        """
        Load JSON data from file

        Handles both single object and array of objects

        Returns:
            List of data dictionaries
        """
        logger.info(f"Loading JSON from: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Convert single object to list
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            raise ValueError(f"Expected JSON object or array, got {type(data).__name__}")

        logger.info(f"Loaded {len(data)} items from JSON")
        return data

    def convert_value(self, value: Any, target_type: str) -> Any:
        """Convert value to appropriate type for Slab field"""
        if value is None or value == '':
            return None

        try:
            if target_type == 'float':
                # Handle string representations of numbers
                if isinstance(value, str):
                    # Remove common characters
                    cleaned = value.strip().replace(',', '').replace('"', '').replace("'", '')
                    return float(cleaned)
                return float(value)

            elif target_type == 'int':
                if isinstance(value, str):
                    cleaned = value.strip().replace(',', '')
                    return int(float(cleaned))  # Handle "10.0" -> 10
                return int(value)

            elif target_type == 'str':
                return str(value).strip()

            elif target_type == 'list':
                if isinstance(value, list):
                    return value
                elif isinstance(value, str):
                    # Try to parse JSON array
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, list):
                            return parsed
                    except json.JSONDecodeError:
                        pass
                    # Otherwise treat as comma-separated
                    return [v.strip() for v in value.split(',') if v.strip()]
                return [value]

            return value

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert {value} to {target_type}: {e}")
            return None

    def process_mapped_fields(self, mapped: dict[str, Any]) -> dict[str, Any]:
        """Process and convert mapped fields to correct types"""
        processed = {}

        # Handle name (required)
        if 'name' in mapped:
            processed['name'] = self.convert_value(mapped['name'], 'str')

        # String fields
        for field in ['stone_type', 'supplier', 'finish', 'color', 'location', 'status']:
            if field in mapped:
                processed[field] = self.convert_value(mapped[field], 'str')

        # Float fields
        for field in ['thickness', 'length', 'width', 'square_feet', 'cost', 'price']:
            if field in mapped:
                processed[field] = self.convert_value(mapped[field], 'float')

        # Integer fields
        if 'quantity' in mapped:
            processed['quantity'] = self.convert_value(mapped['quantity'], 'int')

        # Tags - join if array
        if 'tags' in mapped:
            tags = self.convert_value(mapped['tags'], 'list')
            if tags:
                processed['tags'] = ', '.join(str(t) for t in tags)

        # Notes
        if 'notes' in mapped:
            processed['notes'] = self.convert_value(mapped['notes'], 'str')

        # Images
        if 'primary_image' in mapped:
            processed['primary_image'] = self.convert_value(mapped['primary_image'], 'str')

        if 'additional_images' in mapped:
            additional = self.convert_value(mapped['additional_images'], 'list')
            if additional:
                processed['additional_images'] = additional

        # Handle dimensions parsing
        if 'dimensions' in mapped and 'length' not in processed and 'width' not in processed:
            length, width = DimensionsParser.parse(str(mapped['dimensions']))
            if length:
                processed['length'] = length
            if width:
                processed['width'] = width

        return processed

    def check_duplicate(self, db: Any, public_id: str, perceptual_hash: Optional[str]) -> bool:
        """
        Check if slab already exists

        Returns:
            True if duplicate found, False otherwise
        """
        # Check by public_id
        existing = db.query(Slab).filter(Slab.public_id == public_id).first()
        if existing:
            logger.warning(f"Duplicate public_id found: {public_id}")
            return True

        # Check by perceptual hash if available
        if perceptual_hash:
            existing_slabs = db.query(Slab).filter(
                Slab.perceptual_hash.isnot(None)
            ).all()

            threshold = getattr(settings, 'duplicate_threshold', 10)

            for slab in existing_slabs:
                if is_duplicate(perceptual_hash, slab.perceptual_hash, threshold):
                    logger.warning(
                        f"Duplicate image detected: {public_id} matches {slab.public_id} "
                        f"(hash similarity within threshold {threshold})"
                    )
                    return True

        return False

    def process_item(self, db: Any, item: dict[str, Any], index: int) -> bool:
        """
        Process a single item from JSON

        Returns:
            True if successful, False otherwise
        """
        try:
            # Map fields
            mapped, unmapped = FieldMapper.map_data(item)

            # Process mapped fields
            slab_data = self.process_mapped_fields(mapped)

            # Validate required fields
            if 'name' not in slab_data or not slab_data['name']:
                error_msg = f"Item {index + 1}: Missing required field 'name'"
                logger.error(error_msg)
                self.errors.append({'item': index + 1, 'error': error_msg})
                return False

            # Generate public ID
            max_attempts = 10
            public_id = None
            for _ in range(max_attempts):
                candidate = generate_short_id(8)
                if not db.query(Slab).filter(Slab.public_id == candidate).first():
                    public_id = candidate
                    break

            if not public_id:
                error_msg = f"Item {index + 1}: Failed to generate unique public_id"
                logger.error(error_msg)
                self.errors.append({'item': index + 1, 'error': error_msg})
                return False

            slab_data['public_id'] = public_id

            # Calculate perceptual hash if image exists
            perceptual_hash = None
            if slab_data.get('primary_image'):
                image_path = Path(slab_data['primary_image'])
                if image_path.exists():
                    perceptual_hash = calculate_perceptual_hash(image_path)
                    if perceptual_hash:
                        slab_data['perceptual_hash'] = perceptual_hash
                    else:
                        self.warnings.append({
                            'item': index + 1,
                            'warning': f"Failed to calculate perceptual hash for {image_path}"
                        })
                else:
                    self.warnings.append({
                        'item': index + 1,
                        'warning': f"Image file not found: {image_path}"
                    })

            # Check for duplicates
            if self.check_duplicate(db, public_id, perceptual_hash):
                logger.info(f"Item {index + 1}: Skipping duplicate - {slab_data['name']}")
                self.stats['skipped'] += 1
                return True  # Not an error, just skipped

            # Store unmapped fields in extra_json
            if unmapped:
                slab_data['extra_json'] = unmapped

            # Set import metadata
            slab_data['import_source'] = 'json_metadata'
            slab_data['import_batch_id'] = self.batch_id

            # Create Slab object
            slab = Slab(**slab_data)

            # Generate QR code (unless dry run)
            if not self.dry_run:
                try:
                    qr_path = generate_qr_code(public_id)
                    slab.qr_code_path = str(qr_path)
                except Exception as e:
                    logger.warning(f"Failed to generate QR code for {public_id}: {e}")
                    self.warnings.append({
                        'item': index + 1,
                        'warning': f"QR code generation failed: {e}"
                    })

            # Save to database (unless dry run)
            if not self.dry_run:
                db.add(slab)
                db.commit()
                logger.info(f"Item {index + 1}/{self.stats['processed']}: Successfully imported - {slab.name} ({public_id})")
            else:
                logger.info(f"Item {index + 1}/{self.stats['processed']}: [DRY RUN] Would import - {slab.name} ({public_id})")

            return True

        except Exception as e:
            error_msg = f"Item {index + 1}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.errors.append({'item': index + 1, 'error': error_msg})
            if not self.dry_run:
                db.rollback()
            return False

    def create_import_log(self, db: Any, source_path: str, start_time: datetime) -> None:
        """Create ImportLog record for this batch"""
        if self.dry_run:
            logger.info("[DRY RUN] Skipping ImportLog creation")
            return

        try:
            import_log = ImportLog(
                batch_id=self.batch_id,
                import_type='json_metadata',
                source_path=source_path,
                status='completed' if self.stats['failed'] == 0 else 'partial',
                items_processed=self.stats['processed'],
                items_success=self.stats['success'],
                items_failed=self.stats['failed'],
                items_skipped=self.stats['skipped'],
                errors=self.errors if self.errors else None,
                warnings=self.warnings if self.warnings else None,
                summary=self.generate_summary(),
                started_at=start_time,
                completed_at=datetime.now(),
            )

            db.add(import_log)
            db.commit()
            logger.info(f"Created ImportLog with batch_id: {self.batch_id}")

        except Exception as e:
            logger.error(f"Failed to create ImportLog: {e}")
            db.rollback()

    def generate_summary(self) -> str:
        """Generate human-readable summary"""
        lines = [
            f"Metadata Import Summary",
            f"Batch ID: {self.batch_id}",
            f"Total Processed: {self.stats['processed']}",
            f"Successful: {self.stats['success']}",
            f"Failed: {self.stats['failed']}",
            f"Skipped (Duplicates): {self.stats['skipped']}",
        ]

        if self.stats['processed'] > 0:
            success_rate = (self.stats['success'] / self.stats['processed']) * 100
            lines.append(f"Success Rate: {success_rate:.1f}%")

        return '\n'.join(lines)

    def print_summary(self) -> None:
        """Print summary report to console"""
        print("\n" + "=" * 60)
        print(self.generate_summary())
        print("=" * 60)

        if self.errors:
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors[:10]:  # Show first 10
                print(f"  - Item {error['item']}: {error['error']}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")

        if self.warnings:
            print(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings[:10]:  # Show first 10
                print(f"  - Item {warning['item']}: {warning['warning']}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more warnings")

        print()

    def run(self, file_path: Path) -> int:
        """
        Run the import process

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        start_time = datetime.now()

        logger.info("=" * 60)
        logger.info("SlabHub Metadata Importer")
        logger.info(f"Batch ID: {self.batch_id}")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        logger.info("=" * 60)

        try:
            # Load JSON data
            items = self.load_json(file_path)

            if not items:
                logger.warning("No items to process")
                return 0

            # Create database session
            db = SessionLocal()

            try:
                # Process each item
                for index, item in enumerate(items):
                    self.stats['processed'] += 1

                    # Show progress
                    if self.stats['processed'] % 10 == 0 or self.stats['processed'] == 1:
                        logger.info(f"Progress: {self.stats['processed']}/{len(items)}")

                    # Process item
                    success = self.process_item(db, item, index)

                    if success:
                        self.stats['success'] += 1
                    else:
                        self.stats['failed'] += 1

                # Create import log
                self.create_import_log(db, str(file_path), start_time)

            finally:
                db.close()

            # Print summary
            self.print_summary()

            # Return exit code
            if self.stats['failed'] > 0:
                logger.warning("Import completed with errors")
                return 1
            else:
                logger.info("Import completed successfully")
                return 0

        except Exception as e:
            logger.error(f"Fatal error during import: {e}", exc_info=True)
            return 1


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Import stone slab metadata from JSON file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import from default file
  python scripts/import_metadata.py

  # Import from custom file
  python scripts/import_metadata.py --file data/imports/stone-identifications.json

  # Preview import without saving (dry run)
  python scripts/import_metadata.py --dry-run

  # Preview custom file
  python scripts/import_metadata.py --file custom.json --dry-run
        """
    )

    parser.add_argument(
        '--file',
        type=str,
        help='Path to JSON file to import (default: settings.import_metadata_file)',
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview import without inserting into database',
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point"""
    args = parse_args()

    # Setup logging
    setup_logging()

    # Determine input file
    if args.file:
        file_path = Path(args.file)
    elif settings.import_metadata_file:
        file_path = Path(settings.import_metadata_file)
    else:
        logger.error(
            "No input file specified. Use --file or set import_metadata_file in settings"
        )
        return 1

    # Verify file exists
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return 1

    # Run import
    importer = MetadataImporter(dry_run=args.dry_run)
    return importer.run(file_path)


if __name__ == '__main__':
    sys.exit(main())
