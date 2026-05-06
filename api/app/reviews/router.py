import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.claims.models import ExtractedClaimRow, UploadedDocumentRow
from app.matching.models import ClaimEvaluationRow
from app.reviews.models import (
    ReviewDecisionRequest,
    ReviewDecisionRow,
    ReviewSessionResponse,
    ReviewSessionRow,
    ReviewStatus,
)
from core.db import get_db

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.get("/")
async def list_reviews(db: AsyncSession = Depends(get_db)):
    """List all review sessions. Powers the review list home screen."""
    stmt = (
        select(ReviewSessionRow)
        .order_by(ReviewSessionRow.created_at.desc())
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    reviews = []
    for s in sessions:
        doc = await db.get(UploadedDocumentRow, s.document_id)
        # Count total claims and reviewed claims
        total = await db.scalar(
            select(func.count(ExtractedClaimRow.id))
            .where(ExtractedClaimRow.document_id == s.document_id)
        )
        reviewed = await db.scalar(
            select(func.count(ReviewDecisionRow.id))
            .where(ReviewDecisionRow.session_id == s.id)
        )
        reviews.append(
            ReviewSessionResponse(
                id=s.id,
                document_id=s.document_id,
                filename=doc.filename if doc else "unknown",
                drug_name=doc.drug_name if doc else None,
                status=ReviewStatus(s.status),
                total_claims=total or 0,
                reviewed_claims=reviewed or 0,
                created_at=s.created_at,
            )
        )

    return {"reviews": reviews}


@router.get("/{review_id}")
async def get_review(review_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a review session with all claim evaluations. Powers the annotated document view."""
    session = await db.get(ReviewSessionRow, review_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Review not found")

    doc = await db.get(UploadedDocumentRow, session.document_id)

    # Get all evaluations with their claims
    result = await db.execute(
        select(ClaimEvaluationRow, ExtractedClaimRow)
        .join(ExtractedClaimRow, ClaimEvaluationRow.claim_id == ExtractedClaimRow.id)
        .where(ExtractedClaimRow.document_id == session.document_id)
    )
    rows = result.all()

    # Get existing decisions
    decisions_result = await db.execute(
        select(ReviewDecisionRow).where(ReviewDecisionRow.session_id == review_id)
    )
    decisions = {d.evaluation_id: d for d in decisions_result.scalars().all()}

    evaluations = []
    for eval_row, claim_row in rows:
        decision = decisions.get(eval_row.id)
        evaluations.append({
            "id": str(eval_row.id),
            "claim_id": str(claim_row.id),
            "claim_text": claim_row.claim_text,
            "start_offset": claim_row.start_offset,
            "end_offset": claim_row.end_offset,
            "status": eval_row.status,
            "reasoning": eval_row.reasoning,
            "citation_text": eval_row.citation_text,
            "citation_section": eval_row.citation_section,
            "citation_verified": eval_row.citation_verified,
            "decision": {
                "action": decision.action,
                "override_reason": decision.override_reason,
                "override_detail": decision.override_detail,
                "decided_at": decision.decided_at.isoformat() if decision.decided_at else None,
            } if decision else None,
        })

    return {
        "review_id": str(session.id),
        "document_id": str(session.document_id),
        "filename": doc.filename if doc else "unknown",
        "drug_name": doc.drug_name if doc else None,
        "extracted_text": doc.extracted_text if doc else None,
        "status": session.status,
        "total_claims": len(evaluations),
        "reviewed_claims": len(decisions),
        "evaluations": evaluations,
    }


@router.post("/{review_id}/claims/{evaluation_id}/decide")
async def decide_claim(
    review_id: UUID,
    evaluation_id: UUID,
    body: ReviewDecisionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a reviewer decision (accept/override/escalate) on a claim."""
    session = await db.get(ReviewSessionRow, review_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Review not found")

    evaluation = await db.get(ClaimEvaluationRow, evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    decision = ReviewDecisionRow(
        evaluation_id=evaluation_id,
        session_id=review_id,
        action=body.action.value,
        override_reason=body.override_reason.value if body.override_reason else None,
        override_detail=body.override_detail,
        override_new_status=body.override_new_status,
    )
    db.add(decision)

    # Check if all claims are reviewed — update session status
    total_claims = await db.scalar(
        select(func.count(ExtractedClaimRow.id))
        .where(ExtractedClaimRow.document_id == session.document_id)
    )
    total_decisions = await db.scalar(
        select(func.count(ReviewDecisionRow.id))
        .where(ReviewDecisionRow.session_id == review_id)
    ) or 0
    # +1 for the decision we just added (not yet committed)
    if (total_decisions + 1) >= (total_claims or 0):
        session.status = ReviewStatus.COMPLETE.value
        session.completed_at = datetime.datetime.utcnow()

    await db.commit()
    await db.refresh(decision)

    return {
        "decision_id": str(decision.id),
        "action": decision.action,
        "session_status": session.status,
    }
