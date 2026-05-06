"""P0 integration tests for the ingestion pipeline.

Uses a mock embedding service — no OpenAI API calls needed.
Tests the full flow: parse XML → extract statements → embed → store in pgvector.
"""

import pathlib

import pytest
from sqlalchemy import create_engine, select, text, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.labels.models import Base, LabelStatementRow
from app.labels.service import ingest_spl_file
from app.labels.spl_parser import parse_spl_xml
from app.labels.statements import extract_statements
from core.embeddings import EmbeddingService

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
DIMENSIONS = 1536


class MockEmbeddingService(EmbeddingService):
    """Returns deterministic fake embeddings for testing."""

    def __init__(self):
        self.embedded_texts: list[str] = []

    def _make_embedding(self, text: str) -> list[float]:
        h = hash(text) % 10000
        vec = [0.0] * DIMENSIONS
        vec[h % DIMENSIONS] = 1.0
        return vec

    async def embed(self, text: str) -> list[float]:
        self.embedded_texts.append(text)
        return self._make_embedding(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.embedded_texts.extend(texts)
        return [self._make_embedding(t) for t in texts]


@pytest.fixture
async def db():
    """Create a test database with pgvector extension."""
    engine = create_async_engine(
        "postgresql+asyncpg://localhost:5432/claims_intelligence",
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        # Clean up test data
        await session.execute(text("DELETE FROM label_statements"))
        await session.commit()

    await engine.dispose()


class TestIngestionE2E:
    """End-to-end ingestion tests with mock embeddings."""

    @pytest.mark.asyncio
    async def test_ingest_metformin_creates_statements(self, db):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        embedding_service = MockEmbeddingService()

        result = await ingest_spl_file(xml, embedding_service, db)

        assert result["drug_name"] == "Metformin hydrochloride"
        assert result["status"] == "ingested"
        assert result["statement_count"] > 0

    @pytest.mark.asyncio
    async def test_ingested_statements_exist_in_db(self, db):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        embedding_service = MockEmbeddingService()

        await ingest_spl_file(xml, embedding_service, db)

        stmt = select(func.count(LabelStatementRow.id))
        result = await db.execute(stmt)
        count = result.scalar()
        assert count > 0

    @pytest.mark.asyncio
    async def test_statements_have_embeddings(self, db):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        embedding_service = MockEmbeddingService()

        await ingest_spl_file(xml, embedding_service, db)

        stmt = select(LabelStatementRow).limit(1)
        result = await db.execute(stmt)
        row = result.scalar_one()
        assert row.embedding is not None
        assert len(row.embedding) == DIMENSIONS

    @pytest.mark.asyncio
    async def test_statements_have_correct_metadata(self, db):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        embedding_service = MockEmbeddingService()

        await ingest_spl_file(xml, embedding_service, db)

        stmt = select(LabelStatementRow).limit(1)
        result = await db.execute(stmt)
        row = result.scalar_one()
        assert row.drug_name == "Metformin hydrochloride"
        assert row.set_id == "17050df5-9e95-4e1b-ac75-34add289b139"
        assert row.section_name  # Should have a section name
        assert row.statement_text  # Should have text

    @pytest.mark.asyncio
    async def test_embedding_service_called_for_each_statement(self, db):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        embedding_service = MockEmbeddingService()

        # Count expected statements
        label = parse_spl_xml(xml)
        expected_count = len(extract_statements(label))

        await ingest_spl_file(xml, embedding_service, db)

        assert len(embedding_service.embedded_texts) == expected_count

    @pytest.mark.asyncio
    async def test_aspirin_ingestion(self, db):
        xml = (FIXTURES / "aspirin_spl.xml").read_bytes()
        embedding_service = MockEmbeddingService()

        result = await ingest_spl_file(xml, embedding_service, db)

        assert result["status"] == "ingested"
        assert result["statement_count"] > 0

    @pytest.mark.asyncio
    async def test_vector_similarity_search(self, db):
        """After ingestion, verify pgvector similarity search works."""
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        embedding_service = MockEmbeddingService()

        await ingest_spl_file(xml, embedding_service, db)

        # Create a query embedding and search
        query_embedding = await embedding_service.embed("type 2 diabetes treatment")
        query_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        result = await db.execute(
            text(f"""
                SELECT drug_name, section_name, statement_text,
                       embedding <=> '{query_str}'::vector AS distance
                FROM label_statements
                ORDER BY distance
                LIMIT 5
            """)
        )
        rows = result.fetchall()
        assert len(rows) > 0
        assert rows[0].drug_name == "Metformin hydrochloride"
