import pathlib
import time

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.labels.models import LabelStatementRow, DrugSearchResult, LabelStatementResponse
from app.labels.service import ingest_spl_file, ingest_spl_directory
from core.db import get_db
from core.openai_embeddings import OpenAIEmbeddingService

router = APIRouter(prefix="/api/labels", tags=["labels"])

# In-memory cache for the drug list (rarely changes, expensive query)
_drugs_cache: dict | None = None
_drugs_cache_time: float = 0
_DRUGS_CACHE_TTL = 300  # 5 minutes


def invalidate_drugs_cache():
    global _drugs_cache, _drugs_cache_time
    _drugs_cache = None
    _drugs_cache_time = 0


def _get_embedding_service() -> OpenAIEmbeddingService:
    return OpenAIEmbeddingService()


@router.post("/ingest/file")
async def ingest_single_file(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    embedding_service: OpenAIEmbeddingService = Depends(_get_embedding_service),
):
    """Upload and ingest a single SPL XML file."""
    content = await file.read()
    result = await ingest_spl_file(content, embedding_service, db)
    invalidate_drugs_cache()
    return result


@router.post("/ingest/directory")
async def ingest_from_directory(
    directory_path: str,
    db: AsyncSession = Depends(get_db),
    embedding_service: OpenAIEmbeddingService = Depends(_get_embedding_service),
):
    """Ingest all SPL XML files from a local directory path."""
    path = pathlib.Path(directory_path)
    if not path.is_dir():
        return {"error": f"Not a directory: {directory_path}"}
    results = await ingest_spl_directory(path, embedding_service, db)
    invalidate_drugs_cache()
    return {"results": results, "total": len(results)}


def _build_grouped_drug_query(filter_clause=None):
    """Build the grouped drug list query with window functions.

    Returns a select statement that groups drugs by case-insensitive name,
    picks the best set_id (most statements), and aggregates counts.
    """
    normalized_name = func.upper(LabelStatementRow.drug_name)

    rank = (
        func.row_number()
        .over(
            partition_by=normalized_name,
            order_by=func.count(LabelStatementRow.id).desc(),
        )
        .label("rn")
    )

    base = select(
        LabelStatementRow.set_id,
        func.max(LabelStatementRow.drug_name).label("drug_name"),
        normalized_name.label("norm_name"),
        func.count(func.distinct(LabelStatementRow.section_name)).label("section_count"),
        func.count(LabelStatementRow.id).label("statement_count"),
        rank,
    )
    if filter_clause is not None:
        base = base.where(filter_clause)
    inner = base.group_by(normalized_name, LabelStatementRow.set_id).subquery()

    totals = (
        select(
            inner.c.norm_name,
            func.sum(inner.c.statement_count).label("total_statements"),
            func.max(inner.c.section_count).label("total_sections"),
        )
        .group_by(inner.c.norm_name)
        .subquery()
    )

    best = (
        select(inner.c.drug_name, inner.c.set_id, inner.c.norm_name)
        .where(inner.c.rn == 1)
        .subquery()
    )

    return (
        select(
            best.c.drug_name,
            best.c.set_id,
            totals.c.total_sections.label("section_count"),
            totals.c.total_statements.label("statement_count"),
        )
        .join(totals, best.c.norm_name == totals.c.norm_name)
        .order_by(best.c.norm_name)
    )


def _rows_to_results(rows):
    return [
        DrugSearchResult(
            drug_name=r.drug_name,
            set_id=r.set_id,
            section_count=r.section_count,
            statement_count=r.statement_count,
        )
        for r in rows
    ]


@router.get("/drugs")
async def list_drugs(db: AsyncSession = Depends(get_db)):
    """List all ingested drugs, grouped by case-insensitive name. Cached."""
    global _drugs_cache, _drugs_cache_time

    if _drugs_cache is not None and (time.time() - _drugs_cache_time) < _DRUGS_CACHE_TTL:
        return _drugs_cache

    stmt = _build_grouped_drug_query()
    result = await db.execute(stmt)
    response = {"drugs": _rows_to_results(result.all())}

    _drugs_cache = response
    _drugs_cache_time = time.time()
    return response


@router.get("/drugs/search")
async def search_drugs(q: str, db: AsyncSession = Depends(get_db)):
    """Search for a drug by name, grouped by case-insensitive name."""
    filter_clause = LabelStatementRow.drug_name.ilike(f"%{q}%")
    stmt = _build_grouped_drug_query(filter_clause)
    result = await db.execute(stmt)
    return {"results": _rows_to_results(result.all())}


@router.get("/drugs/{set_id}/statements")
async def get_drug_statements(set_id: str, db: AsyncSession = Depends(get_db)):
    """Get all label statements for a specific drug. Powers the label lookup drawer."""
    stmt = (
        select(LabelStatementRow)
        .where(LabelStatementRow.set_id == set_id)
        .order_by(LabelStatementRow.section_name, LabelStatementRow.id)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {
        "statements": [
            LabelStatementResponse(
                id=r.id,
                drug_name=r.drug_name,
                set_id=r.set_id,
                section_name=r.section_name,
                statement_text=r.statement_text,
                ingested_at=r.ingested_at,
            )
            for r in rows
        ]
    }
