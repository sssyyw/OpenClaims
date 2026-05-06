"""Tests for label statement extraction."""

import pathlib

from app.labels.spl_parser import parse_spl_xml
from app.labels.statements import extract_statements

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class TestStatementExtraction:
    def test_metformin_produces_statements(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        statements = extract_statements(label)
        assert len(statements) > 0

    def test_all_statements_have_drug_name(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        statements = extract_statements(label)
        for s in statements:
            assert s.drug_name == "Metformin hydrochloride"

    def test_all_statements_have_set_id(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        statements = extract_statements(label)
        for s in statements:
            assert s.set_id == "17050df5-9e95-4e1b-ac75-34add289b139"

    def test_all_statements_have_section_name(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        statements = extract_statements(label)
        for s in statements:
            assert s.section_name

    def test_statements_include_indications(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        statements = extract_statements(label)
        indications = [s for s in statements if "Indications" in s.section_name]
        assert len(indications) > 0
        # Should mention type 2 diabetes
        texts = " ".join(s.text for s in indications)
        assert "type 2 diabetes" in texts

    def test_statements_include_dosage_subsections(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        statements = extract_statements(label)
        dosage_subs = [s for s in statements if ">" in s.section_name]
        assert len(dosage_subs) > 0

    def test_no_very_short_fragments(self):
        """All statements should be at least 20 chars — no fragments like '(1)'."""
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        statements = extract_statements(label)
        for s in statements:
            assert len(s.text) >= 20, f"Too short: '{s.text}'"

    def test_no_xml_markup_in_statements(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        statements = extract_statements(label)
        for s in statements:
            assert "<" not in s.text, f"XML markup found: '{s.text[:80]}'"

    def test_aspirin_produces_statements(self):
        xml = (FIXTURES / "aspirin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        statements = extract_statements(label)
        assert len(statements) > 0
