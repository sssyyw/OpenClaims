"""Database and API models for review sessions and reviewer decisions."""

import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.labels.models import Base


class ReviewStatus(str, Enum):
    PROCESSING = "PROCESSING"
    IN_REVIEW = "IN_REVIEW"
    COMPLETE = "COMPLETE"


class ReviewActionType(str, Enum):
    ACCEPT = "ACCEPT"
    OVERRIDE = "OVERRIDE"
    ESCALATE = "ESCALATE"


class OverrideReason(str, Enum):
    LABEL_LANGUAGE_EQUIVALENT = "Label language is equivalent"
    WITHIN_FAIR_BALANCE = "Within fair balance"
    SUPPORTED_BY_OTHER_SECTION = "Supported by other section"
    OTHER = "Other"


class ReviewSessionRow(Base):
    """A review session for an uploaded document."""

    __tablename__ = "review_sessions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("uploaded_documents.id"), nullable=False)
    status = Column(String(20), nullable=False, default=ReviewStatus.PROCESSING.value)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime)


class ReviewDecisionRow(Base):
    """A reviewer's decision on a single claim evaluation."""

    __tablename__ = "review_decisions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    evaluation_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("claim_evaluations.id"), nullable=False
    )
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("review_sessions.id"), nullable=False)
    action = Column(String(20), nullable=False)
    override_reason = Column(String(100))
    override_detail = Column(Text)
    override_new_status = Column(String(30))
    decided_at = Column(DateTime, default=datetime.datetime.utcnow)


# API models


class ReviewSessionResponse(BaseModel):
    id: UUID
    document_id: UUID
    filename: str
    drug_name: str | None
    status: ReviewStatus
    total_claims: int
    reviewed_claims: int
    created_at: datetime.datetime


class ReviewDecisionRequest(BaseModel):
    action: ReviewActionType
    override_reason: OverrideReason | None = None
    override_detail: str | None = None
    override_new_status: str | None = None
