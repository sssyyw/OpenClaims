from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.claims.parser import DocumentParseError, UnsupportedFormatError
from app.claims.service import parse_document
from app.matching.service import evaluate_document
from core.claude_evaluator import ClaudeEvaluator
from core.db import get_db
from core.llm import ClaimEvaluator
from core.openai_embeddings import OpenAIEmbeddingService

router = APIRouter(prefix="/api/claims", tags=["claims"])


def _get_evaluator() -> ClaimEvaluator:
    return ClaudeEvaluator()


def _get_embedding_service() -> OpenAIEmbeddingService:
    return OpenAIEmbeddingService()


@router.post("/parse")
async def parse_uploaded_document(
    file: UploadFile,
    drug_name: str | None = None,
    db: AsyncSession = Depends(get_db),
    evaluator: ClaimEvaluator = Depends(_get_evaluator),
):
    """Upload a promotional document (PDF/DOCX), extract text and claims.

    Returns the document ID, extracted text length, and list of claims
    with character offsets for inline highlighting in the annotated view.
    """
    content = await file.read()

    try:
        result = await parse_document(
            file_bytes=content,
            filename=file.filename or "unknown",
            evaluator=evaluator,
            db=db,
            drug_name=drug_name,
        )
    except UnsupportedFormatError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DocumentParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return result


@router.post("/evaluate/{document_id}")
async def evaluate_claims(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    evaluator: ClaimEvaluator = Depends(_get_evaluator),
    embedding_service: OpenAIEmbeddingService = Depends(_get_embedding_service),
):
    """Evaluate all claims in a document against FDA label statements.

    Runs the matching pipeline: embed → retrieve → LLM evaluate → citation verify.
    All claims processed in parallel (max 5 concurrent).
    Returns when all claims are evaluated (all-at-once).
    """
    try:
        result = await evaluate_document(
            document_id=document_id,
            evaluator=evaluator,
            embedding_service=embedding_service,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result
