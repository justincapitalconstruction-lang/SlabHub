#!/usr/bin/env python3
"""
Build Reference Catalog from CSV

Converts product line CSV into JSON reference catalog for SlabHub.
Normalizes product names and creates basic catalog structure.

Usage:
    python scripts/build_reference_catalog_from_csv.py
    python scripts/build_reference_catalog_from_csv.py --csv path/to/products.csv
    python scripts/build_reference_catalog_from_csv.py --output data/reference_catalog.json
"""

import argparse
import csv
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings

logger = logging.getLogger(__name__)


class CatalogBuilder:
    """Builds reference catalog from CSV data"""

    def __init__(self):
        self.catalog = {
            "catalog_version": "2.0.0",
            "created_at": None,
            "total_entries": 0,
            "entries": []
        }

    def normalize_product_name(self, name: str) -> str:
        """
        Normalize product name for consistency

        Args:
            name: Raw product name from CSV

        Returns:
            Normalized product name
        """
        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower().strip()

        # Fix common typos and variations
        corrections = {
            "valnev     valley": "valle nevado",
            "valnev valley": "valle nevado",
            "caramelato": "caramellato",
            "viscon white": "viscount white",
            "whtie dallas": "white dallas",
            "ice white": "white ice",
            "chapa": "chapa bloco",  # Assuming this is a placeholder
            "giallo fiortofino": "giallo fiorito",
            "palau java": "palau java quartz",
            "star blanc": "star blanc quartz",
            "venetian wave": "venetian wave",
            "bianco superiore quartzite": "bianco superiore",
            "swan quartzite": "swan quartzite",
            "silver macaubas": "silver macaubas",
            "river white": "river white",
            "ocean blue": "ocean blue quartzite",
            "colonial cream": "colonial cream",
            "kozmus": "cosmos",
            "giallo napoli": "giallo napoli",
            "bordeaux river": "bordeaux river",
            "bianco antico": "bianco antico",
            "jaguar": "jaguar",
            "tidal white": "tidal white",
            "forest": "forest green",
            "negresco": "negresco",
            "santa cecilia white": "santa cecilia white",
            "caravelas": "caravelas gold",
            "snowfall": "snowfall",
            "bianco tropical": "bianco tropical",
            "new caladonia": "new caledonia",
            "new venetian gold": "new venetian gold",
            "hawaii": "hawaii",
            "tan brown": "tan brown",
            "azul cafe": "azul cafe",
            "sierra river": "sierra river",
            "black soapstone": "black soapstone",
            "giallo ornamental": "giallo ornamental",
            "legacy white": "legacy white",
            "blue diamond": "blue diamond",
            "red verona": "red verona",
            "santa cecilia": "santa cecilia",
            "juparana colombo": "juparana colombo",
            "black galaxy": "black galaxy",
            "blue barracuda": "blue barracuda",
        }

        # Apply corrections
        normalized = corrections.get(normalized, normalized)

        # Title case
        normalized = normalized.title()

        # Fix specific capitalizations
        normalized = re.sub(r'\bQuartzite\b', 'Quartzite', normalized)
        normalized = re.sub(r'\bQuartz\b', 'Quartz', normalized)

        return normalized

    def detect_stone_type(self, name: str) -> str:
        """
        Detect stone type from product name

        Args:
            name: Product name

        Returns:
            Stone type (granite, marble, quartzite, quartz, soapstone)
        """
        name_lower = name.lower()

        # Quartz products
        if any(term in name_lower for term in ['quartz', 'silestone', 'caesarstone']):
            return 'quartz'

        # Quartzite
        if 'quartzite' in name_lower:
            return 'quartzite'

        # Soapstone
        if 'soapstone' in name_lower:
            return 'soapstone'

        # Marble
        if any(term in name_lower for term in ['marble', 'verona', 'bianco', 'carrara']):
            return 'marble'

        # Default to granite (most common)
        return 'granite'

    def build_catalog_from_csv(self, csv_path: Path) -> Dict[str, Any]:
        """
        Build catalog from CSV file

        Args:
            csv_path: Path to CSV file

        Returns:
            Catalog dictionary
        """
        logger.info(f"Building catalog from CSV: {csv_path}")

        entries = []

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                # Try to detect delimiter
                sample = f.read(1024)
                f.seek(0)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter

                reader = csv.DictReader(f, delimiter=delimiter)

                for row_num, row in enumerate(reader, 1):
                    # Get product name (try different column names)
                    product_name = None
                    for col in ['Product Name', 'product_name', 'name', 'Name']:
                        if col in row and row[col].strip():
                            product_name = row[col].strip()
                            break

                    if not product_name:
                        logger.warning(f"Row {row_num}: No product name found, skipping")
                        continue

                    # Normalize name
                    normalized_name = self.normalize_product_name(product_name)

                    # Detect stone type
                    stone_type = self.detect_stone_type(normalized_name)

                    # Build entry
                    entry = {
                        "name": normalized_name,
                        "original_name": product_name,
                        "stone_type": stone_type,
                        "tags": [],  # Will be populated by GPT enrichment
                        "aliases": [],  # Will be populated by GPT enrichment
                        "category": stone_type,
                        "description": "",  # Will be populated by GPT enrichment
                        "typical_colors": "",  # Will be populated by GPT enrichment
                        "grain_pattern_type": "",  # Will be populated by GPT enrichment
                        "common_finish_options": "",  # Will be populated by GPT enrichment
                        "typical_applications": "",  # Will be populated by GPT enrichment
                        "known_aliases_or_variants": []  # Will be populated by GPT enrichment
                    }

                    entries.append(entry)
                    logger.debug(f"Added entry: {normalized_name}")

        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            raise

        # Update catalog
        from datetime import datetime
        self.catalog.update({
            "created_at": datetime.now().isoformat(),
            "total_entries": len(entries),
            "entries": entries
        })

        logger.info(f"Built catalog with {len(entries)} entries")
        return self.catalog

    def save_catalog(self, output_path: Path) -> None:
        """
        Save catalog to JSON file

        Args:
            output_path: Output file path
        """
        logger.info(f"Saving catalog to: {output_path}")

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.catalog, f, indent=2, ensure_ascii=False)

        logger.info(f"Catalog saved successfully")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Build reference catalog from CSV")
    parser.add_argument(
        '--csv',
        type=Path,
        default=Path('data/Reference list - Sheet1.csv'),
        help='Path to CSV file (default: data/Reference list - Sheet1.csv)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('data/reference_catalog.json'),
        help='Output JSON file path (default: data/reference_catalog.json)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    # Check if CSV exists
    if not args.csv.exists():
        logger.error(f"CSV file not found: {args.csv}")
        sys.exit(1)

    # Build catalog
    builder = CatalogBuilder()
    try:
        catalog = builder.build_catalog_from_csv(args.csv)
        builder.save_catalog(args.output)
        logger.info("✅ Catalog build completed successfully!")
        logger.info(f"📊 Total entries: {catalog['total_entries']}")
        logger.info(f"💾 Saved to: {args.output}")
    except Exception as e:
        logger.error(f"❌ Catalog build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()