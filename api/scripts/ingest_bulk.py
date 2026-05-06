"""Bulk ingest DailyMed monthly update SPL files.

Usage:
    python scripts/ingest_bulk.py /path/to/dm_spl_monthly_update_feb2026/
    python scripts/ingest_bulk.py /path/to/dm_spl_monthly_update_feb2026/ --categories prescription otc
    python scripts/ingest_bulk.py /path/to/dm_spl_monthly_update_feb2026/ --limit 10

Handles the nested DailyMed directory structure:
  dm_spl_monthly_update/
    prescription/   ← zip files
    otc/
    homeopathic/
    animal/
    other/
"""

import argparse
import asyncio
import logging
import pathlib
import sys
import time

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.labels.models import Base
from app.labels.service import ingest_spl_file, _ingest_zip
from core.db import engine, async_session
from core.openai_embeddings import OpenAIEmbeddingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

ALL_CATEGORIES = ["prescription", "otc", "homeopathic", "animal", "other"]


async def main():
    parser = argparse.ArgumentParser(description="Bulk ingest DailyMed SPL files")
    parser.add_argument("directory", type=pathlib.Path, help="Path to unzipped DailyMed update")
    parser.add_argument("--categories", nargs="+", default=ALL_CATEGORIES, help="Categories to ingest")
    parser.add_argument("--limit", type=int, default=0, help="Max files per category (0=all)")
    parser.add_argument("--skip-errors", action="store_true", default=True, help="Continue on errors")
    args = parser.parse_args()

    root = args.directory
    if not root.is_dir():
        print(f"Error: {root} is not a directory")
        sys.exit(1)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    embedding_service = OpenAIEmbeddingService()

    total_ingested = 0
    total_statements = 0
    total_errors = 0
    total_skipped = 0
    start_time = time.time()

    for category in args.categories:
        cat_dir = root / category
        if not cat_dir.is_dir():
            logger.warning(f"Category directory not found: {cat_dir}")
            continue

        zip_files = sorted(cat_dir.glob("*.zip"))
        if args.limit:
            zip_files = zip_files[: args.limit]

        logger.info(f"=== {category.upper()} === ({len(zip_files)} files)")

        for i, zip_file in enumerate(zip_files, 1):
            try:
                async with async_session() as db:
                    results = await _ingest_zip(zip_file, embedding_service, db)

                for r in results:
                    status = r.get("status", "")
                    if status == "ingested":
                        total_ingested += 1
                        total_statements += r.get("statement_count", 0)
                        if i % 50 == 0 or i == len(zip_files):
                            logger.info(
                                f"  [{category}] {i}/{len(zip_files)} — "
                                f"{r['drug_name']}: {r['statement_count']} stmts"
                            )
                    elif status == "skipped":
                        total_skipped += 1
                    elif status == "error":
                        total_errors += 1

            except Exception as e:
                total_errors += 1
                logger.error(f"  [{category}] {i}/{len(zip_files)} FAILED {zip_file.name}: {e}")
                if not args.skip_errors:
                    raise

    elapsed = time.time() - start_time
    logger.info(
        f"\n{'='*60}\n"
        f"DONE in {elapsed:.0f}s\n"
        f"  Ingested: {total_ingested} drugs, {total_statements} statements\n"
        f"  Skipped:  {total_skipped} (no statements)\n"
        f"  Errors:   {total_errors}\n"
        f"{'='*60}"
    )

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
