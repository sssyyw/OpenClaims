"""Label ingestion service — end-to-end pipeline from SPL XML to pgvector.

Pipeline: download/read SPL XML → parse → extract statements → embed → store.
"""

import logging
import pathlib
import zipfile

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.labels.models import LabelStatementRow
from app.labels.spl_parser import parse_spl_xml
from app.labels.statements import extract_statements
from core.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


async def ingest_spl_file(
    xml_content: bytes,
    embedding_service: EmbeddingService,
    db: AsyncSession,
) -> dict:
    """Ingest a single SPL XML file into the database.

    Returns a summary dict with drug_name, set_id, and statement_count.
    """
    label = parse_spl_xml(xml_content)
    statements = extract_statements(label)

    if not statements:
        logger.warning(f"No statements extracted from {label.drug_name} ({label.set_id})")
        return {
            "drug_name": label.drug_name,
            "set_id": label.set_id,
            "statement_count": 0,
            "status": "skipped",
        }

    # Remove existing statements for this label (dedup on re-ingest)
    await db.execute(
        delete(LabelStatementRow).where(LabelStatementRow.set_id == label.set_id)
    )

    # Embed all statements in a batch
    texts = [s.text for s in statements]
    embeddings = await embedding_service.embed_batch(texts)

    # Store in database
    for statement, embedding in zip(statements, embeddings):
        row = LabelStatementRow(
            drug_name=statement.drug_name,
            set_id=statement.set_id,
            manufacturer=label.manufacturer,
            section_name=statement.section_name,
            statement_text=statement.text,
            embedding=embedding,
            spl_version=label.version,
        )
        db.add(row)

    await db.commit()

    logger.info(f"Ingested {len(statements)} statements for {label.drug_name}")
    return {
        "drug_name": label.drug_name,
        "set_id": label.set_id,
        "statement_count": len(statements),
        "status": "ingested",
    }


async def ingest_spl_directory(
    directory: pathlib.Path,
    embedding_service: EmbeddingService,
    db: AsyncSession,
) -> list[dict]:
    """Ingest all SPL XML files from a directory.

    Handles both raw .xml files and .zip files containing XML.
    """
    results = []

    # Process .xml files directly
    for xml_file in sorted(directory.glob("*.xml")):
        try:
            xml_content = xml_file.read_bytes()
            result = await ingest_spl_file(xml_content, embedding_service, db)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to ingest {xml_file.name}: {e}")
            results.append({"file": xml_file.name, "status": "error", "error": str(e)})

    # Process .zip files (DailyMed bulk download format)
    for zip_file in sorted(directory.glob("*.zip")):
        try:
            results.extend(await _ingest_zip(zip_file, embedding_service, db))
        except Exception as e:
            logger.error(f"Failed to process zip {zip_file.name}: {e}")
            results.append({"file": zip_file.name, "status": "error", "error": str(e)})

    return results


async def _ingest_zip(
    zip_path: pathlib.Path,
    embedding_service: EmbeddingService,
    db: AsyncSession,
) -> list[dict]:
    """Extract and ingest SPL XML files from a DailyMed bulk download zip."""
    results = []

    with zipfile.ZipFile(zip_path) as zf:
        xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
        logger.info(f"Found {len(xml_names)} XML files in {zip_path.name}")

        for xml_name in xml_names:
            try:
                xml_content = zf.read(xml_name)
                result = await ingest_spl_file(xml_content, embedding_service, db)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to ingest {xml_name} from {zip_path.name}: {e}")
                results.append({"file": xml_name, "status": "error", "error": str(e)})

    return results


async def create_tables(db: AsyncSession) -> None:
    """Create database tables if they don't exist."""
    from app.labels.models import Base
    from app.claims.models import UploadedDocumentRow, ExtractedClaimRow  # noqa: F401
    from app.matching.models import ClaimEvaluationRow  # noqa: F401
    from app.reviews.models import ReviewSessionRow, ReviewDecisionRow  # noqa: F401

    async with db.bind.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
