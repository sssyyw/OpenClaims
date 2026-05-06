"""Claude implementation of the ClaimEvaluator interface.

Uses Anthropic's Claude API for:
1. Extracting promotional claims from document text (with character offsets)
2. Evaluating claims against label statements (classification + reasoning + citation)
"""

import json
import logging

import anthropic

from core.config import settings
from core.llm import (
    ClaimEvaluation,
    ClaimEvaluator,
    ClaimStatus,
    LabelStatement,
    PromotionalClaim,
)

logger = logging.getLogger(__name__)

EXTRACT_CLAIMS_PROMPT = """You are an FDA regulatory reviewer assistant. Your task is to identify individual promotional claims from a pharmaceutical promotional document.

A "promotional claim" is any statement that makes a specific assertion about a drug's:
- Efficacy (e.g., "reduces mortality by 30%")
- Safety (e.g., "well-tolerated with minimal side effects")
- Indication (e.g., "indicated for first-line treatment")
- Superiority or comparison (e.g., "superior to standard chemotherapy")
- Patient outcomes (e.g., "median OS of 30 months")

Do NOT include:
- General marketing language without specific claims (e.g., "Ask your doctor")
- Drug name mentions without claims
- Section headers or formatting text

For each claim, provide:
- The exact text of the claim as it appears in the document
- The character offset where the claim starts in the document text
- The character offset where the claim ends

Return a JSON array of objects with fields: "text", "start_offset", "end_offset".
Only return the JSON array, no other text.

Document text:
{document_text}"""

EVALUATE_CLAIM_PROMPT = """You are an FDA regulatory reviewer assistant. Your task is to evaluate whether a promotional claim is supported by the FDA-approved drug label.

CLASSIFICATION:
- SUPPORTED: The claim is directly and fully supported by the label text
- PARTIALLY_SUPPORTED: The claim is partially supported but includes details not in the label (e.g., specific percentages, broader populations)
- NEEDS_REVIEW: The claim may be related to the label but the connection is ambiguous
- UNSUPPORTED: The claim has no basis in the provided label statements

RULES:
1. Be strict about specificity — if the claim adds numbers, populations, or qualifiers not in the label, it's PARTIALLY_SUPPORTED at best
2. Marketing superlatives ("best", "#1", "superior") are UNSUPPORTED unless the label explicitly supports them
3. Safety claims must match the label's adverse reaction profile exactly
4. Always provide a direct quote from the label as your citation

Return a JSON object with fields:
- "status": one of SUPPORTED, PARTIALLY_SUPPORTED, NEEDS_REVIEW, UNSUPPORTED
- "reasoning": 2-3 sentences explaining your classification
- "citation_text": exact quote from the label statements that is most relevant (or null if UNSUPPORTED)
- "citation_section": the section name the citation comes from (or null)

Only return the JSON object, no other text.

Promotional claim:
"{claim_text}"

FDA-approved label statements:
{label_statements}"""


class ClaudeEvaluator(ClaimEvaluator):
    def __init__(self, client: anthropic.AsyncAnthropic | None = None):
        self.client = client or anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model

    async def extract_claims(self, document_text: str) -> list[PromotionalClaim]:
        prompt = EXTRACT_CLAIMS_PROMPT.format(document_text=document_text)

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text.strip()

            # Parse JSON response — handle markdown code blocks
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            claims_data = json.loads(content)
            return [
                PromotionalClaim(
                    text=c["text"],
                    start_offset=c.get("start_offset"),
                    end_offset=c.get("end_offset"),
                )
                for c in claims_data
            ]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse claim extraction response: {e}")
            logger.error(f"Raw response: {content[:500]}")
            return []
        except anthropic.APITimeoutError:
            logger.error("Claude API timeout during claim extraction")
            return []
        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            return []

    async def evaluate_claim(
        self, claim: PromotionalClaim, label_statements: list[LabelStatement]
    ) -> ClaimEvaluation:
        # Format label statements for the prompt
        formatted_statements = "\n".join(
            f"[{s.section_name}] {s.text}" for s in label_statements
        )

        prompt = EVALUATE_CLAIM_PROMPT.format(
            claim_text=claim.text,
            label_statements=formatted_statements,
        )

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text.strip()

            # Parse JSON response
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            result = json.loads(content)
            return ClaimEvaluation(
                claim=claim,
                status=ClaimStatus(result["status"]),
                reasoning=result["reasoning"],
                citation_text=result.get("citation_text"),
                citation_section=result.get("citation_section"),
                matched_label_statements=label_statements,
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse evaluation response: {e}")
            return ClaimEvaluation(
                claim=claim,
                status=ClaimStatus.NEEDS_REVIEW,
                reasoning=f"Evaluation produced unparseable response. Marked for manual review.",
                matched_label_statements=label_statements,
            )
        except anthropic.APITimeoutError:
            logger.error(f"Claude API timeout evaluating claim: {claim.text[:50]}")
            return ClaimEvaluation(
                claim=claim,
                status=ClaimStatus.NEEDS_REVIEW,
                reasoning="Evaluation timed out. Marked for manual review.",
                matched_label_statements=label_statements,
            )
        except Exception as e:
            logger.error(f"Claim evaluation failed: {e}")
            return ClaimEvaluation(
                claim=claim,
                status=ClaimStatus.NEEDS_REVIEW,
                reasoning=f"Evaluation failed: {e}. Marked for manual review.",
                matched_label_statements=label_statements,
            )
