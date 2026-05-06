"""Database and API models for promotional claims and document uploads."""

import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.labels.models import Base


class DocumentFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"


class UploadedDocumentRow(Base):
    """An uploaded promotional document."""

    __tablename__ = "uploaded_documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    filename = Column(String(500), nullable=False)
    format = Column(String(10), nullable=False)
    extracted_text = Column(Text)
    claim_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    drug_name = Column(String(255))


class ExtractedClaimRow(Base):
    """A promotional claim extracted from an uploaded document."""

    __tablename__ = "extracted_claims"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("uploaded_documents.id"), nullable=False)
    claim_text = Column(Text, nullable=False)
    start_offset = Column(Integer)
    end_offset = Column(Integer)
    extracted_at = Column(DateTime, default=datetime.datetime.utcnow)


# API models


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    claim_count: int


class ExtractedClaimResponse(BaseModel):
    id: UUID
    claim_text: str
    start_offset: int | None
    end_offset: int | None
