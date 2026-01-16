#!/usr/bin/env python3
"""
Enrich Reference Catalog with GPT-4.0

Uses GPT-4.0 to add detailed descriptions, colors, patterns, and other
attributes to the reference catalog entries.

Usage:
    python scripts/enrich_reference_catalog_gpt.py
    python scripts/enrich_reference_catalog_gpt.py --catalog data/reference_catalog.json
    python scripts/enrich_reference_catalog_gpt.py --limit 10 --overwrite
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import settings

logger = logging.getLogger(__name__)


class CatalogEnricher:
    """Enriches catalog entries with GPT-4.0"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Please add OPENAI_API_KEY=your-key-here to .env"
            )

        self.client = OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(Exception)
    )
    def enrich_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich a single catalog entry with GPT-4.0

        Args:
            entry: Catalog entry to enrich

        Returns:
            Enriched entry
        """
        product_name = entry['name']
        stone_type = entry.get('stone_type', 'granite')

        logger.info(f"Enriching: {product_name}")

        prompt = f"""
You are a stone industry expert. Provide detailed information about the granite/quartzite product: "{product_name}"

Please respond with a JSON object containing exactly these fields:

{{
  "description": "A detailed 2-3 sentence description of this stone's appearance, origin, and characteristics",
  "typical_colors": "Primary and secondary colors, described precisely (e.g., 'Light gray base with white and taupe speckles')",
  "grain_pattern_type": "Pattern type - one of: speckled, veined, uniform, mixed (with brief explanation)",
  "common_finish_options": "Typical finishes: polished, honed, leathered, etc.",
  "typical_applications": "Common uses: countertops, flooring, walls, etc.",
  "known_aliases_or_variants": ["List", "of", "alternative", "names", "or", "variations"]
}}

Be specific and accurate. If you don't know exact details, provide educated estimates based on similar stones.
"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a stone industry expert providing accurate information about natural stone products. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )

            content = response.choices[0].message.content.strip()

            # Try to parse JSON
            try:
                enrichment = json.loads(content)
            except json.JSONDecodeError:
                # Sometimes GPT returns with markdown code blocks
                if content.startswith('```json'):
                    content = content[7:]
                if content.endswith('```'):
                    content = content[:-3]
                enrichment = json.loads(content.strip())

            # Update entry
            entry.update({
                'description': enrichment.get('description', ''),
                'typical_colors': enrichment.get('typical_colors', ''),
                'grain_pattern_type': enrichment.get('grain_pattern_type', ''),
                'common_finish_options': enrichment.get('common_finish_options', ''),
                'typical_applications': enrichment.get('typical_applications', ''),
                'known_aliases_or_variants': enrichment.get('known_aliases_or_variants', [])
            })

            logger.info(f"✅ Enriched: {product_name}")
            return entry

        except Exception as e:
            logger.error(f"❌ Failed to enrich {product_name}: {e}")
            # Return original entry unchanged
            return entry

    def enrich_catalog(self, catalog_path: Path, limit: Optional[int] = None,
                      overwrite: bool = False) -> Dict[str, Any]:
        """
        Enrich all catalog entries

        Args:
            catalog_path: Path to catalog JSON
            limit: Maximum entries to process
            overwrite: Whether to re-enrich already enriched entries

        Returns:
            Updated catalog
        """
        logger.info(f"Loading catalog: {catalog_path}")

        with open(catalog_path, 'r', encoding='utf-8') as f:
            catalog = json.load(f)

        entries = catalog.get('entries', [])
        logger.info(f"Found {len(entries)} entries")

        enriched_count = 0
        skipped_count = 0

        for i, entry in enumerate(entries):
            if limit and enriched_count >= limit:
                logger.info(f"Reached limit of {limit} entries")
                break

            # Skip if already enriched and not overwriting
            if not overwrite and entry.get('description'):
                logger.debug(f"Skipping already enriched: {entry['name']}")
                skipped_count += 1
                continue

            # Enrich entry
            enriched_entry = self.enrich_entry(entry)
            entries[i] = enriched_entry
            enriched_count += 1

            # Rate limiting
            time.sleep(0.5)

        # Update catalog metadata
        from datetime import datetime
        catalog['enriched_at'] = datetime.now().isoformat()
        catalog['enriched_count'] = enriched_count
        catalog['skipped_count'] = skipped_count

        logger.info(f"Enrichment complete: {enriched_count} enriched, {skipped_count} skipped")
        return catalog

    def save_catalog(self, catalog: Dict[str, Any], output_path: Path) -> None:
        """
        Save enriched catalog

        Args:
            catalog: Catalog data
            output_path: Output path
        """
        logger.info(f"Saving enriched catalog to: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, indent=2, ensure_ascii=False)

        logger.info("✅ Catalog saved successfully")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Enrich reference catalog with GPT-4.0")
    parser.add_argument(
        '--catalog',
        type=Path,
        default=Path('data/reference_catalog.json'),
        help='Path to catalog JSON file'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output file path (default: overwrite input file)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum entries to process'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Re-enrich already enriched entries'
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

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY not found in environment")
        logger.error("Please add OPENAI_API_KEY=your-key-here to your .env file")
        sys.exit(1)

    # Check catalog exists
    if not args.catalog.exists():
        logger.error(f"❌ Catalog file not found: {args.catalog}")
        sys.exit(1)

    # Set output path
    output_path = args.output or args.catalog

    # Enrich catalog
    enricher = CatalogEnricher()
    try:
        catalog = enricher.enrich_catalog(args.catalog, args.limit, args.overwrite)
        enricher.save_catalog(catalog, output_path)

        enriched = catalog.get('enriched_count', 0)
        skipped = catalog.get('skipped_count', 0)
        total = catalog.get('total_entries', 0)

        logger.info("✅ Catalog enrichment completed!")
        logger.info(f"📊 Total entries: {total}")
        logger.info(f"🔄 Enriched: {enriched}")
        logger.info(f"⏭️  Skipped: {skipped}")
        logger.info(f"💾 Saved to: {output_path}")

    except Exception as e:
        logger.error(f"❌ Enrichment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()