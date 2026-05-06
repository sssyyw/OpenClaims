"""P0 tests for the promotional claim parser.

Tests document extraction (PDF/DOCX), claim extraction (mocked LLM),
error handling for corrupted files and unsupported formats.
"""

import pathlib

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.claims.parser import (
    DocumentParseError,
    UnsupportedFormatError,
    extract_pdf,
    extract_docx,
    extract_text,
)
from app.claims.service import parse_document
from app.labels.models import Base
from core.llm import (
    ClaimEvaluation,
    ClaimEvaluator,
    ClaimStatus,
    LabelStatement,
    PromotionalClaim,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


# --- Mock evaluator for testing claim extraction ---


class MockClaimEvaluator(ClaimEvaluator):
    """Returns predictable claims for testing the pipeline."""

    def __init__(self, claims: list[PromotionalClaim] | None = None):
        self.claims = [
            PromotionalClaim(text="reduces mortality by 30%", start_offset=100, end_offset=125),
            PromotionalClaim(text="well-tolerated with minimal side effects", start_offset=200, end_offset=241),
        ] if claims is None else claims
        self.extract_calls: list[str] = []

    async def extract_claims(self, document_text: str) -> list[PromotionalClaim]:
        self.extract_calls.append(document_text)
        return self.claims

    async def evaluate_claim(
        self, claim: PromotionalClaim, label_statements: list[LabelStatement]
    ) -> ClaimEvaluation:
        return ClaimEvaluation(
            claim=claim,
            status=ClaimStatus.NEEDS_REVIEW,
            reasoning="Mock evaluation",
        )


# --- PDF extraction tests ---


class TestPdfExtraction:
    def test_extract_sample_promo_pdf(self):
        pdf_bytes = (FIXTURES / "sample_promo.pdf").read_bytes()
        text = extract_pdf(pdf_bytes)
        assert "KEYTRUDA" in text
        assert "reduces mortality" in text

    def test_extract_pdf_returns_string(self):
        pdf_bytes = (FIXTURES / "sample_promo.pdf").read_bytes()
        text = extract_pdf(pdf_bytes)
        assert isinstance(text, str)
        assert len(text) > 100

    def test_corrupted_pdf_raises_error(self):
        with pytest.raises(DocumentParseError):
            extract_pdf(b"this is not a PDF file at all")

    def test_empty_pdf_raises_error(self):
        """A valid PDF with no text should raise DocumentParseError."""
        import fitz
        doc = fitz.open()
        doc.new_page()  # blank page
        empty_pdf = doc.tobytes()
        doc.close()
        with pytest.raises(DocumentParseError, match="no extractable text"):
            extract_pdf(empty_pdf)


# --- DOCX extraction tests ---


class TestDocxExtraction:
    def test_corrupted_docx_raises_error(self):
        with pytest.raises(DocumentParseError):
            extract_docx(b"this is not a DOCX file")


# --- Format routing tests ---


class TestExtractText:
    def test_pdf_extension_routes_to_pdf(self):
        pdf_bytes = (FIXTURES / "sample_promo.pdf").read_bytes()
        text = extract_text(pdf_bytes, "promo.pdf")
        assert "KEYTRUDA" in text

    def test_unsupported_format_raises(self):
        with pytest.raises(UnsupportedFormatError, match="Unsupported format"):
            extract_text(b"data", "promo.jpg")

    def test_no_extension_raises(self):
        with pytest.raises(UnsupportedFormatError):
            extract_text(b"data", "noextension")


# --- End-to-end parse_document tests (mocked LLM) ---


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
        # Clean up before AND after each test
        await session.execute(text("DELETE FROM extracted_claims"))
        await session.execute(text("DELETE FROM uploaded_documents"))
        await session.commit()
        yield session
        await session.execute(text("DELETE FROM extracted_claims"))
        await session.execute(text("DELETE FROM uploaded_documents"))
        await session.commit()
    await engine.dispose()


class TestParseDocument:
    @pytest.mark.asyncio
    async def test_parse_pdf_extracts_claims(self, db):
        pdf_bytes = (FIXTURES / "sample_promo.pdf").read_bytes()
        evaluator = MockClaimEvaluator()

        result = await parse_document(
            file_bytes=pdf_bytes,
            filename="promo.pdf",
            evaluator=evaluator,
            db=db,
            drug_name="Keytruda",
        )

        assert result["claim_count"] == 2
        assert result["filename"] == "promo.pdf"
        assert result["drug_name"] == "Keytruda"
        assert len(result["claims"]) == 2

    @pytest.mark.asyncio
    async def test_claims_have_offsets(self, db):
        pdf_bytes = (FIXTURES / "sample_promo.pdf").read_bytes()
        evaluator = MockClaimEvaluator()

        result = await parse_document(
            file_bytes=pdf_bytes,
            filename="promo.pdf",
            evaluator=evaluator,
            db=db,
        )

        for claim in result["claims"]:
            assert "start_offset" in claim
            assert "end_offset" in claim

    @pytest.mark.asyncio
    async def test_evaluator_receives_document_text(self, db):
        pdf_bytes = (FIXTURES / "sample_promo.pdf").read_bytes()
        evaluator = MockClaimEvaluator()

        await parse_document(
            file_bytes=pdf_bytes,
            filename="promo.pdf",
            evaluator=evaluator,
            db=db,
        )

        assert len(evaluator.extract_calls) == 1
        assert "KEYTRUDA" in evaluator.extract_calls[0]

    @pytest.mark.asyncio
    async def test_no_claims_found(self, db):
        pdf_bytes = (FIXTURES / "sample_promo.pdf").read_bytes()
        evaluator = MockClaimEvaluator(claims=[])

        result = await parse_document(
            file_bytes=pdf_bytes,
            filename="promo.pdf",
            evaluator=evaluator,
            db=db,
        )

        assert result["claim_count"] == 0
        assert result["claims"] == []

    @pytest.mark.asyncio
    async def test_document_persisted_to_db(self, db):
        pdf_bytes = (FIXTURES / "sample_promo.pdf").read_bytes()
        evaluator = MockClaimEvaluator()

        result = await parse_document(
            file_bytes=pdf_bytes,
            filename="promo.pdf",
            evaluator=evaluator,
            db=db,
        )

        # Verify document exists in DB
        from sqlalchemy import select, func
        from app.claims.models import UploadedDocumentRow
        count = await db.scalar(select(func.count(UploadedDocumentRow.id)))
        assert count >= 1
