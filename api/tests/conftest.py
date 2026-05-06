"""Shared test fixtures for the claims intelligence API."""

import pytest

from core.llm import (
    ClaimEvaluation,
    ClaimEvaluator,
    ClaimStatus,
    LabelStatement,
    PromotionalClaim,
)


class MockEvaluator(ClaimEvaluator):
    """Mock LLM evaluator for unit tests. No real API calls."""

    def __init__(self, responses: dict[str, ClaimEvaluation] | None = None):
        self.responses = responses or {}
        self.extract_calls: list[str] = []
        self.evaluate_calls: list[tuple[PromotionalClaim, list[LabelStatement]]] = []

    async def extract_claims(self, document_text: str) -> list[PromotionalClaim]:
        self.extract_calls.append(document_text)
        return [
            PromotionalClaim(text="reduces mortality by 30%", start_offset=0, end_offset=27),
        ]

    async def evaluate_claim(
        self, claim: PromotionalClaim, label_statements: list[LabelStatement]
    ) -> ClaimEvaluation:
        self.evaluate_calls.append((claim, label_statements))
        if claim.text in self.responses:
            return self.responses[claim.text]
        return ClaimEvaluation(
            claim=claim,
            status=ClaimStatus.NEEDS_REVIEW,
            reasoning="Mock evaluation — not a real LLM response",
        )


@pytest.fixture
def mock_evaluator():
    return MockEvaluator()
