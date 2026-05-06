"""Semantic matching service — the intelligence layer.

Pipeline per claim:
  1. Embed the promotional claim
  2. pgvector cosine similarity → top-K label statements
  3. LLM evaluation → classification + reasoning + citation
  4. Citation verification → pass or downgrade to NEEDS_REVIEW

All claims in a document are evaluated in parallel (asyncio semaphore, max 5 concurrent).
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.claims.models import ExtractedClaimRow, UploadedDocumentRow
from app.labels.models import LabelStatementRow
from app.matching.citation import verify_citation
from app.matching.models import ClaimEvaluationRow
from app.reviews.models import ReviewSessionRow, ReviewStatus
from core.config import settings
from core.embeddings import EmbeddingService
from core.llm import (
    ClaimEvaluation,
    ClaimEvaluator,
    ClaimStatus,
    LabelStatement,
    PromotionalClaim,
)

logger = logging.getLogger(__name__)


async def evaluate_document(
    document_id: UUID,
    evaluator: ClaimEvaluator,
    embedding_service: EmbeddingService,
    db: AsyncSession,
) -> dict:
    """Run the full matching pipeline for all claims in a document.

    Creates a review session, evaluates all claims in parallel,
    and returns complete results.
    """
    # 1. Load document and its claims
    doc = await db.get(UploadedDocumentRow, document_id)
    if doc is None:
        raise ValueError(f"Document {document_id} not found")

    claims_result = await db.execute(
        select(ExtractedClaimRow).where(ExtractedClaimRow.document_id == document_id)
    )
    claim_rows = list(claims_result.scalars().all())

    if not claim_rows:
        raise ValueError(f"No claims found for document {document_id}")

    # 2. Create review session
    session = ReviewSessionRow(
        document_id=document_id,
        status=ReviewStatus.PROCESSING.value,
    )
    db.add(session)
    await db.flush()

    # 3. Evaluate all claims in parallel
    semaphore = asyncio.Semaphore(settings.llm_max_concurrent)
    tasks = [
        _evaluate_single_claim(
            claim_row=row,
            evaluator=evaluator,
            embedding_service=embedding_service,
            db=db,
            semaphore=semaphore,
        )
        for row in claim_rows
    ]
    evaluations = await asyncio.gather(*tasks, return_exceptions=True)

    # 4. Process results — persist evaluations, handle errors
    eval_results = []
    for claim_row, result in zip(claim_rows, evaluations):
        if isinstance(result, Exception):
            logger.error(f"Evaluation failed for claim '{claim_row.claim_text[:50]}': {result}")
            eval_row = ClaimEvaluationRow(
                claim_id=claim_row.id,
                status=ClaimStatus.NEEDS_REVIEW.value,
                reasoning=f"Evaluation failed: {result}. Marked for manual review.",
                citation_verified=False,
            )
        else:
            eval_row = result
        db.add(eval_row)
        eval_results.append(eval_row)

    # 5. Update review session status
    session.status = ReviewStatus.IN_REVIEW.value
    await db.commit()

    # Refresh to get generated IDs
    for er in eval_results:
        await db.refresh(er)

    # 6. Build response
    status_counts = _count_statuses(eval_results)

    return {
        "review_id": str(session.id),
        "document_id": str(document_id),
        "filename": doc.filename,
        "drug_name": doc.drug_name,
        "total_claims": len(claim_rows),
        **status_counts,
        "evaluations": [
            {
                "id": str(er.id),
                "claim_id": str(er.claim_id),
                "claim_text": cr.claim_text,
                "start_offset": cr.start_offset,
                "end_offset": cr.end_offset,
                "status": er.status,
                "reasoning": er.reasoning,
                "citation_text": er.citation_text,
                "citation_section": er.citation_section,
                "citation_verified": er.citation_verified,
            }
            for er, cr in zip(eval_results, claim_rows)
        ],
    }


async def _evaluate_single_claim(
    claim_row: ExtractedClaimRow,
    evaluator: ClaimEvaluator,
    embedding_service: EmbeddingService,
    db: AsyncSession,
    semaphore: asyncio.Semaphore,
) -> ClaimEvaluationRow:
    """Evaluate a single claim through the full pipeline.

    Runs under the semaphore to limit concurrent LLM calls.
    """
    async with semaphore:
        claim = PromotionalClaim(
            text=claim_row.claim_text,
            start_offset=claim_row.start_offset,
            end_offset=claim_row.end_offset,
        )

        # Stage 1: Embed claim and retrieve top-K label statements
        label_statements = await _retrieve_label_statements(
            claim_text=claim.text,
            embedding_service=embedding_service,
            db=db,
            top_k=settings.retrieval_top_k,
        )

        if not label_statements:
            return ClaimEvaluationRow(
                claim_id=claim_row.id,
                status=ClaimStatus.NEEDS_REVIEW.value,
                reasoning="No matching drug labels found in the database. Cannot evaluate this claim.",
                citation_verified=False,
            )

        # Stage 2: LLM evaluation
        evaluation = await evaluator.evaluate_claim(claim, label_statements)

        # Stage 3: Citation verification
        citation_verified = False
        if evaluation.citation_text:
            # Verify against all label statement texts
            all_label_text = " ".join(s.text for s in label_statements)
            citation_verified = verify_citation(evaluation.citation_text, all_label_text)

            if not citation_verified:
                # Hard gate: downgrade to NEEDS_REVIEW if citation fails
                logger.warning(
                    f"Citation verification failed for claim: {claim.text[:50]}. "
                    f"Downgrading from {evaluation.status} to NEEDS_REVIEW."
                )
                original_status = evaluation.status
                evaluation = ClaimEvaluation(
                    claim=evaluation.claim,
                    status=ClaimStatus.NEEDS_REVIEW,
                    reasoning=(
                        f"Original assessment: {original_status}. "
                        f"{evaluation.reasoning} "
                        f"[Citation could not be verified against source label — downgraded to NEEDS_REVIEW]"
                    ),
                    citation_text=evaluation.citation_text,
                    citation_section=evaluation.citation_section,
                    matched_label_statements=evaluation.matched_label_statements,
                )

        return ClaimEvaluationRow(
            claim_id=claim_row.id,
            status=evaluation.status.value,
            reasoning=evaluation.reasoning,
            citation_text=evaluation.citation_text,
            citation_section=evaluation.citation_section,
            citation_verified=citation_verified,
        )


async def _retrieve_label_statements(
    claim_text: str,
    embedding_service: EmbeddingService,
    db: AsyncSession,
    top_k: int = 10,
) -> list[LabelStatement]:
    """Embed a claim and retrieve the top-K most similar label statements from pgvector."""
    claim_embedding = await embedding_service.embed(claim_text)
    embedding_str = "[" + ",".join(str(x) for x in claim_embedding) + "]"

    result = await db.execute(
        text("""
            SELECT drug_name, set_id, section_name, statement_text,
                   embedding <=> CAST(:embedding AS vector) AS distance
            FROM label_statements
            ORDER BY distance
            LIMIT :top_k
        """),
        {"embedding": embedding_str, "top_k": top_k},
    )
    rows = result.fetchall()

    return [
        LabelStatement(
            text=row.statement_text,
            drug_name=row.drug_name,
            section_name=row.section_name,
            set_id=row.set_id,
        )
        for row in rows
    ]


def _count_statuses(evaluations: list[ClaimEvaluationRow]) -> dict:
    counts = {
        "supported": 0,
        "partially_supported": 0,
        "needs_review": 0,
        "unsupported": 0,
    }
    for e in evaluations:
        key = e.status.lower()
        if key in counts:
            counts[key] += 1
    return counts
