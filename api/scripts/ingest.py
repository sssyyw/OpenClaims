"""CLI script to ingest SPL XML files into the database.

Usage:
    python scripts/ingest.py /path/to/spl/files/

Ingests all .xml and .zip files in the given directory.
Requires: PostgreSQL running, OpenAI API key in .env or CI_OPENAI_API_KEY env var.
"""

import asyncio
import pathlib
import sys

# Add project root to path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from app.labels.models import Base
from app.labels.service import ingest_spl_directory, ingest_spl_file
from core.db import engine, async_session
from core.openai_embeddings import OpenAIEmbeddingService


async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest.py <path-to-spl-files-or-single-xml>")
        sys.exit(1)

    target = pathlib.Path(sys.argv[1])

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    embedding_service = OpenAIEmbeddingService()

    async with async_session() as db:
        if target.is_file() and target.suffix == ".xml":
            print(f"Ingesting single file: {target.name}")
            xml_content = target.read_bytes()
            result = await ingest_spl_file(xml_content, embedding_service, db)
            print(f"  {result['drug_name']}: {result['statement_count']} statements ({result['status']})")
        elif target.is_dir():
            print(f"Ingesting directory: {target}")
            results = await ingest_spl_directory(target, embedding_service, db)
            for r in results:
                if "drug_name" in r:
                    print(f"  {r['drug_name']}: {r.get('statement_count', 0)} statements ({r['status']})")
                else:
                    print(f"  {r.get('file', '?')}: {r['status']} — {r.get('error', '')}")
            print(f"\nTotal: {len(results)} files processed")
        else:
            print(f"Error: {target} is not a valid XML file or directory")
            sys.exit(1)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
