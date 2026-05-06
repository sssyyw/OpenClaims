"""
ClaimEvaluator interface — abstracts LLM calls for claim extraction and evaluation.

MATCHING PIPELINE
=================

Promotional Claim
       │
       ▼
┌──────────────┐
│ Embed claim  │  ◄── OpenAI text-embedding-3-large
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ pgvector     │  ◄── Top-10 label statements by similarity
│ retrieval    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ ClaimEval-   │  ◄── Claim + top-10 label statements
│ uator        │  ──► Classification + reasoning + citation
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Citation     │  ◄── Verify quoted text exists in source label
│ verification │  ──► Pass: show to reviewer / Fail: downgrade to NEEDS_REVIEW
└──────────────┘

Decision 2: Two-stage pipeline. Vector similarity for retrieval ONLY.
LLM provides the final classification with natural-language reasoning.
No blended numeric score.
"""

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel


class ClaimStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    UNSUPPORTED = "UNSUPPORTED"


class PromotionalClaim(BaseModel):
    text: str
    start_offset: int | None = None
    end_offset: int | None = None


class LabelStatement(BaseModel):
    text: str
    drug_name: str
    section_name: str
    set_id: str


class ClaimEvaluation(BaseModel):
    claim: PromotionalClaim
    status: ClaimStatus
    reasoning: str
    citation_text: str | None = None
    citation_section: str | None = None
    matched_label_statements: list[LabelStatement] = []


class ClaimEvaluator(ABC):
    """Abstract interface for LLM-powered claim extraction and evaluation.

    Implementations: ClaudeEvaluator (production), MockEvaluator (tests).
    Enables model swapping (Claude → GPT-4 → local) without touching pipeline code.
    """

    @abstractmethod
    async def extract_claims(self, document_text: str) -> list[PromotionalClaim]:
        """Extract individual promotional claims from document text."""
        ...

    @abstractmethod
    async def evaluate_claim(
        self, claim: PromotionalClaim, label_statements: list[LabelStatement]
    ) -> ClaimEvaluation:
        """Evaluate a single claim against retrieved label statements.

        Returns classification (SUPPORTED/PARTIALLY_SUPPORTED/NEEDS_REVIEW/UNSUPPORTED)
        with natural-language reasoning and a citation quote.
        """
        ...
