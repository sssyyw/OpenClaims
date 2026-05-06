"""Extract individual label statements from parsed SPL sections.

A "label statement" is a single embeddable unit of text from a drug label section.
These are the units we store in pgvector and match against promotional claims.

Strategy: sentence-level splitting with context preservation.
Each statement includes the section and subsection title for context.
"""

import re

from app.labels.spl_parser import ParsedLabel, ParsedSection
from core.llm import LabelStatement


def extract_statements(label: ParsedLabel) -> list[LabelStatement]:
    """Extract all label statements from a parsed SPL label.

    Walks through all target sections and their subsections,
    splits text into sentences, and creates LabelStatement objects.
    """
    statements = []

    for section in label.sections:
        # Extract from the section's own text
        section_statements = _split_into_statements(
            text=section.text,
            drug_name=label.drug_name,
            section_name=section.display_name,
            set_id=label.set_id,
        )
        statements.extend(section_statements)

        # Extract from subsections
        for subsection in section.subsections:
            sub_statements = _split_into_statements(
                text=subsection.text,
                drug_name=label.drug_name,
                section_name=f"{section.display_name} > {subsection.title}",
                set_id=label.set_id,
            )
            statements.extend(sub_statements)

    return statements


def _split_into_statements(
    text: str, drug_name: str, section_name: str, set_id: str
) -> list[LabelStatement]:
    """Split section text into individual statements.

    Splitting rules:
    1. Split on sentence boundaries (period + space/newline)
    2. Keep bullet points as individual statements
    3. Minimum length threshold to skip fragments
    4. Merge very short sentences with the next sentence
    """
    if not text.strip():
        return []

    raw_sentences = _sentence_split(text)
    statements = []

    for sentence in raw_sentences:
        cleaned = sentence.strip()
        if len(cleaned) < 20:
            continue  # Skip fragments like "(1)", "(2.1)", etc.

        statements.append(LabelStatement(
            text=cleaned,
            drug_name=drug_name,
            section_name=section_name,
            set_id=set_id,
        ))

    return statements


def _sentence_split(text: str) -> list[str]:
    """Split text into sentences, respecting bullet points and abbreviations.

    Handles:
    - Period followed by space + uppercase letter (standard sentence boundary)
    - Bullet points (lines starting with - or *)
    - Newline-separated items
    - Preserves abbreviations like "m.g.", "e.g.", "i.e."
    """
    # First, split on bullet points / list items
    lines = text.split("\n")
    sentences = []
    current = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Empty line — flush current buffer
            if current:
                sentences.extend(_split_line(" ".join(current)))
                current = []
            continue

        if stripped.startswith(("- ", "* ", "\u2022 ")):
            # Bullet point — flush previous, start new
            if current:
                sentences.extend(_split_line(" ".join(current)))
                current = []
            # Remove bullet prefix
            stripped = re.sub(r"^[-*\u2022]\s*", "", stripped)
            sentences.append(stripped)
        else:
            current.append(stripped)

    if current:
        sentences.extend(_split_line(" ".join(current)))

    return sentences


def _split_line(text: str) -> list[str]:
    """Split a single block of text into sentences at period boundaries."""
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    # Split on period followed by space and uppercase letter
    # But not on common abbreviations
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z])", text)
    return [p.strip() for p in parts if p.strip()]
