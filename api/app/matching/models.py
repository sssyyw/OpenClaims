"""Database and API models for claim evaluation results."""

import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.labels.models import Base
from core.llm import ClaimStatus


class ClaimEvaluationRow(Base):
    """Result of evaluating a promotional claim against label statements."""

    __tablename__ = "claim_evaluations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    claim_id = Column(PG_UUID(as_uuid=True), ForeignKey("extracted_claims.id"), nullable=False)
    status = Column(String(30), nullable=False)
    reasoning = Column(Text, nullable=False)
    citation_text = Column(Text)
    citation_section = Column(String(255))
    citation_verified = Column(Boolean, default=False)
    evaluated_at = Column(DateTime, default=datetime.datetime.utcnow)


# API models


class ClaimEvaluationResponse(BaseModel):
    id: UUID
    claim_id: UUID
    claim_text: str
    start_offset: int | None
    end_offset: int | None
    status: ClaimStatus
    reasoning: str
    citation_text: str | None
    citation_section: str | None
    citation_verified: bool


class DocumentEvaluationResponse(BaseModel):
    document_id: UUID
    filename: str
    drug_name: str | None
    total_claims: int
    supported: int
    partially_supported: int
    needs_review: int
    unsupported: int
    evaluations: list[ClaimEvaluationResponse]
