"""Claims service — document upload, text extraction, and claim extraction."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.claims.models import ExtractedClaimRow, UploadedDocumentRow
from app.claims.parser import extract_text
from core.llm import ClaimEvaluator

logger = logging.getLogger(__name__)


async def parse_document(
    file_bytes: bytes,
    filename: str,
    evaluator: ClaimEvaluator,
    db: AsyncSession,
    drug_name: str | None = None,
) -> dict:
    """Upload, extract text, and extract claims from a promotional document.

    Returns document ID and extracted claims.
    """
    # 1. Extract text from document
    document_text = extract_text(file_bytes, filename)

    # 2. Persist the uploaded document
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "unknown"
    doc_row = UploadedDocumentRow(
        filename=filename,
        format=ext,
        extracted_text=document_text,
        drug_name=drug_name,
    )
    db.add(doc_row)
    await db.flush()  # Get the generated ID

    # 3. Extract claims using the LLM
    claims = await evaluator.extract_claims(document_text)

    # 4. Persist extracted claims
    claim_rows = []
    for claim in claims:
        claim_row = ExtractedClaimRow(
            document_id=doc_row.id,
            claim_text=claim.text,
            start_offset=claim.start_offset,
            end_offset=claim.end_offset,
        )
        db.add(claim_row)
        claim_rows.append(claim_row)

    # Update document claim count
    doc_row.claim_count = len(claims)
    await db.commit()

    logger.info(f"Parsed {filename}: {len(claims)} claims extracted")

    return {
        "document_id": str(doc_row.id),
        "filename": filename,
        "drug_name": drug_name,
        "extracted_text_length": len(document_text),
        "claim_count": len(claims),
        "claims": [
            {
                "id": str(row.id),
                "text": row.claim_text,
                "start_offset": row.start_offset,
                "end_offset": row.end_offset,
            }
            for row in claim_rows
        ],
    }
