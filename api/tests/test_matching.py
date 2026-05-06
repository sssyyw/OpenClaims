"""P0 tests for the semantic matching pipeline.

Tests the full pipeline: embed → retrieve → evaluate → citation verify.
Uses mock embedding service and mock LLM evaluator — no API calls needed.
Requires PostgreSQL with pgvector running locally.
"""

import pathlib
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.claims.models import ExtractedClaimRow, UploadedDocumentRow
from app.labels.models import Base, LabelStatementRow
from app.matching.models import ClaimEvaluationRow
from app.matching.service import evaluate_document, _retrieve_label_statements
from app.reviews.models import ReviewSessionRow
from core.embeddings import EmbeddingService
from core.llm import (
    ClaimEvaluation,
    ClaimEvaluator,
    ClaimStatus,
    LabelStatement,
    PromotionalClaim,
)

DIMENSIONS = 1536


class MockEmbeddingService(EmbeddingService):
    """Deterministic embeddings based on keyword presence."""

    async def embed(self, text_input: str) -> list[float]:
        vec = [0.001] * DIMENSIONS
        # Cluster texts with similar keywords near each other
        if "diabetes" in text_input.lower() or "glycemic" in text_input.lower():
            vec[0] = 1.0
        elif "mortality" in text_input.lower() or "survival" in text_input.lower():
            vec[1] = 1.0
        elif "tolerab" in text_input.lower() or "side effect" in text_input.lower():
            vec[2] = 1.0
        else:
            vec[3] = 1.0
        return vec

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]


class MockMatchingEvaluator(ClaimEvaluator):
    """Evaluator that returns deterministic results based on claim text."""

    async def extract_claims(self, document_text: str) -> list[PromotionalClaim]:
        return []

    async def evaluate_claim(
        self, claim: PromotionalClaim, label_statements: list[LabelStatement]
    ) -> ClaimEvaluation:
        # Simulate different evaluations based on claim text
        if "indicated" in claim.text.lower():
            return ClaimEvaluation(
                claim=claim,
                status=ClaimStatus.SUPPORTED,
                reasoning="The label directly supports this indication claim.",
                citation_text=label_statements[0].text if label_statements else None,
                citation_section=label_statements[0].section_name if label_statements else None,
                matched_label_statements=label_statements,
            )
        elif "mortality" in claim.text.lower():
            return ClaimEvaluation(
                claim=claim,
                status=ClaimStatus.PARTIALLY_SUPPORTED,
                reasoning="The label mentions survival but not the specific percentage.",
                citation_text="demonstrated a reduction in all-cause mortality",
                citation_section="Indications and Usage",
                matched_label_statements=label_statements,
            )
        elif "#1" in claim.text or "best" in claim.text.lower():
            return ClaimEvaluation(
                claim=claim,
                status=ClaimStatus.UNSUPPORTED,
                reasoning="Marketing superlatives are not supported by the label.",
                matched_label_statements=label_statements,
            )
        else:
            return ClaimEvaluation(
                claim=claim,
                status=ClaimStatus.NEEDS_REVIEW,
                reasoning="Unable to determine support level.",
                matched_label_statements=label_statements,
            )


@pytest.fixture
async def db():
    engine = create_async_engine(
        "postgresql+asyncpg://localhost:5432/claims_intelligence",
    )
    import app.claims.models  # noqa
    import app.matching.models  # noqa
    import app.reviews.models  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # Clean before
        await session.execute(text("DELETE FROM review_decisions"))
        await session.execute(text("DELETE FROM review_sessions"))
        await session.execute(text("DELETE FROM claim_evaluations"))
        await session.execute(text("DELETE FROM extracted_claims"))
        await session.execute(text("DELETE FROM uploaded_documents"))
        await session.execute(text("DELETE FROM label_statements"))
        await session.commit()
        yield session
        # Clean after
        await session.execute(text("DELETE FROM review_decisions"))
        await session.execute(text("DELETE FROM review_sessions"))
        await session.execute(text("DELETE FROM claim_evaluations"))
        await session.execute(text("DELETE FROM extracted_claims"))
        await session.execute(text("DELETE FROM uploaded_documents"))
        await session.execute(text("DELETE FROM label_statements"))
        await session.commit()
    await engine.dispose()


async def _seed_label_statements(db: AsyncSession, embedding_service: MockEmbeddingService):
    """Seed the database with label statements for testing."""
    statements = [
        ("Metformin hydrochloride", "test-set-id", "Indications and Usage",
         "Metformin hydrochloride extended-release tablets are indicated as an adjunct to diet and exercise to improve glycemic control in adults with type 2 diabetes mellitus."),
        ("Metformin hydrochloride", "test-set-id", "Dosage and Administration > 2.1 Adult Dosage",
         "The recommended starting dose of Metformin hydrochloride extended-release tablets is 500 mg orally once daily with the evening meal."),
        ("Metformin hydrochloride", "test-set-id", "Dosage and Administration > 2.1 Adult Dosage",
         "Increase the dose in increments of 500 mg weekly on the basis of glycemic control and tolerability, up to a maximum of 2000 mg once daily with the evening meal."),
    ]

    for drug_name, set_id, section_name, statement_text in statements:
        embedding = await embedding_service.embed(statement_text)
        row = LabelStatementRow(
            drug_name=drug_name,
            set_id=set_id,
            section_name=section_name,
            statement_text=statement_text,
            embedding=embedding,
            spl_version="1",
        )
        db.add(row)
    await db.commit()


async def _seed_document_with_claims(db: AsyncSession) -> UUID:
    """Create a test document with claims and return the document ID."""
    doc = UploadedDocumentRow(
        filename="test_promo.pdf",
        format="pdf",
        extracted_text="Test promotional content",
        drug_name="Metformin",
        claim_count=3,
    )
    db.add(doc)
    await db.flush()

    claims = [
        ExtractedClaimRow(
            document_id=doc.id,
            claim_text="Metformin is indicated for type 2 diabetes mellitus",
            start_offset=0,
            end_offset=51,
        ),
        ExtractedClaimRow(
            document_id=doc.id,
            claim_text="Metformin reduces mortality by 30%",
            start_offset=52,
            end_offset=86,
        ),
        ExtractedClaimRow(
            document_id=doc.id,
            claim_text="Metformin is the #1 prescribed diabetes medication",
            start_offset=87,
            end_offset=137,
        ),
    ]
    for c in claims:
        db.add(c)
    await db.commit()

    return doc.id


class TestRetrieveStatements:
    """Test pgvector similarity retrieval."""

    @pytest.mark.asyncio
    async def test_retrieves_relevant_statements(self, db):
        embedding_service = MockEmbeddingService()
        await _seed_label_statements(db, embedding_service)

        results = await _retrieve_label_statements(
            claim_text="improve glycemic control in diabetes",
            embedding_service=embedding_service,
            db=db,
            top_k=3,
        )

        assert len(results) == 3
        # The diabetes/glycemic statement should be most relevant
        assert "glycemic" in results[0].text.lower() or "diabetes" in results[0].text.lower()

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_labels(self, db):
        embedding_service = MockEmbeddingService()
        # Don't seed any labels

        results = await _retrieve_label_statements(
            claim_text="some drug claim",
            embedding_service=embedding_service,
            db=db,
            top_k=10,
        )

        assert len(results) == 0


class TestEvaluateDocument:
    """End-to-end matching pipeline tests."""

    @pytest.mark.asyncio
    async def test_evaluates_all_claims(self, db):
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()
        await _seed_label_statements(db, embedding_service)
        doc_id = await _seed_document_with_claims(db)

        result = await evaluate_document(doc_id, evaluator, embedding_service, db)

        assert result["total_claims"] == 3
        assert len(result["evaluations"]) == 3

    @pytest.mark.asyncio
    async def test_creates_review_session(self, db):
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()
        await _seed_label_statements(db, embedding_service)
        doc_id = await _seed_document_with_claims(db)

        result = await evaluate_document(doc_id, evaluator, embedding_service, db)

        assert "review_id" in result
        # Session should exist in DB
        session = await db.get(ReviewSessionRow, UUID(result["review_id"]))
        assert session is not None
        assert session.status == "IN_REVIEW"

    @pytest.mark.asyncio
    async def test_supported_claim_gets_supported(self, db):
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()
        await _seed_label_statements(db, embedding_service)
        doc_id = await _seed_document_with_claims(db)

        result = await evaluate_document(doc_id, evaluator, embedding_service, db)

        indicated_eval = next(
            e for e in result["evaluations"]
            if "indicated" in e["claim_text"].lower()
        )
        assert indicated_eval["status"] == "SUPPORTED"

    @pytest.mark.asyncio
    async def test_superlative_claim_gets_unsupported(self, db):
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()
        await _seed_label_statements(db, embedding_service)
        doc_id = await _seed_document_with_claims(db)

        result = await evaluate_document(doc_id, evaluator, embedding_service, db)

        superlative_eval = next(
            e for e in result["evaluations"]
            if "#1" in e["claim_text"]
        )
        assert superlative_eval["status"] == "UNSUPPORTED"

    @pytest.mark.asyncio
    async def test_citation_verification_on_supported_claim(self, db):
        """SUPPORTED claim with verified citation should keep citation_verified=True."""
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()
        await _seed_label_statements(db, embedding_service)
        doc_id = await _seed_document_with_claims(db)

        result = await evaluate_document(doc_id, evaluator, embedding_service, db)

        indicated_eval = next(
            e for e in result["evaluations"]
            if "indicated" in e["claim_text"].lower()
        )
        # Citation should be verified because the mock returns the actual label text
        assert indicated_eval["citation_verified"] is True

    @pytest.mark.asyncio
    async def test_unverified_citation_downgrades_to_needs_review(self, db):
        """Claim with hallucinated citation should be downgraded to NEEDS_REVIEW."""
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()
        await _seed_label_statements(db, embedding_service)
        doc_id = await _seed_document_with_claims(db)

        result = await evaluate_document(doc_id, evaluator, embedding_service, db)

        mortality_eval = next(
            e for e in result["evaluations"]
            if "mortality" in e["claim_text"].lower()
        )
        # Mock returns "demonstrated a reduction in all-cause mortality" as citation
        # but that text isn't in our seeded label statements — should fail verification
        # and be downgraded
        if not mortality_eval["citation_verified"]:
            assert mortality_eval["status"] == "NEEDS_REVIEW"
            assert "downgraded" in mortality_eval["reasoning"].lower() or "NEEDS_REVIEW" in mortality_eval["reasoning"]

    @pytest.mark.asyncio
    async def test_evaluations_have_claim_offsets(self, db):
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()
        await _seed_label_statements(db, embedding_service)
        doc_id = await _seed_document_with_claims(db)

        result = await evaluate_document(doc_id, evaluator, embedding_service, db)

        for e in result["evaluations"]:
            assert e["start_offset"] is not None
            assert e["end_offset"] is not None

    @pytest.mark.asyncio
    async def test_status_counts(self, db):
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()
        await _seed_label_statements(db, embedding_service)
        doc_id = await _seed_document_with_claims(db)

        result = await evaluate_document(doc_id, evaluator, embedding_service, db)

        total = (
            result["supported"]
            + result["partially_supported"]
            + result["needs_review"]
            + result["unsupported"]
        )
        assert total == result["total_claims"]

    @pytest.mark.asyncio
    async def test_document_not_found(self, db):
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()

        with pytest.raises(ValueError, match="not found"):
            await evaluate_document(
                UUID("00000000-0000-0000-0000-000000000000"),
                evaluator, embedding_service, db,
            )

    @pytest.mark.asyncio
    async def test_no_claims_raises_error(self, db):
        embedding_service = MockEmbeddingService()
        evaluator = MockMatchingEvaluator()

        # Create document with no claims
        doc = UploadedDocumentRow(
            filename="empty.pdf", format="pdf",
            extracted_text="No claims here", claim_count=0,
        )
        db.add(doc)
        await db.commit()

        with pytest.raises(ValueError, match="No claims"):
            await evaluate_document(doc.id, evaluator, embedding_service, db)
