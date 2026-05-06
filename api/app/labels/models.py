"""Database and API models for FDA drug labels."""

import datetime
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase

from pgvector.sqlalchemy import Vector

from core.config import settings


class Base(DeclarativeBase):
    pass


class LabelStatementRow(Base):
    """A single extractable statement from an FDA drug label section."""

    __tablename__ = "label_statements"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    drug_name = Column(String(255), nullable=False, index=True)
    set_id = Column(String(255), nullable=False, index=True)
    manufacturer = Column(String(255), nullable=True, default="")
    section_name = Column(String(255), nullable=False)
    statement_text = Column(Text, nullable=False)
    embedding = Column(Vector(settings.embedding_dimensions))
    ingested_at = Column(DateTime, default=datetime.datetime.utcnow)
    spl_version = Column(String(50))

    __table_args__ = (
        Index(
            "ix_label_statements_embedding",
            embedding,
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# API response models


class LabelStatementResponse(BaseModel):
    id: UUID
    drug_name: str
    set_id: str
    section_name: str
    statement_text: str
    ingested_at: datetime.datetime


class DrugSearchResult(BaseModel):
    drug_name: str
    set_id: str
    section_count: int
    statement_count: int
