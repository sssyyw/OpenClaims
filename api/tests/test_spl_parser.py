"""Tests for SPL XML parsing — P0 coverage for the ingestion pipeline."""

import pathlib

import pytest

from app.labels.spl_parser import ParsedLabel, parse_spl_xml

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class TestParseSplXml:
    """Tests against real DailyMed SPL XML files."""

    def test_metformin_drug_name(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        assert label.drug_name == "Metformin hydrochloride"

    def test_metformin_set_id(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        assert label.set_id == "17050df5-9e95-4e1b-ac75-34add289b139"

    def test_metformin_version(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        assert label.version == "23"

    def test_metformin_extracts_indications_section(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        indications = [s for s in label.sections if s.loinc_code == "34067-9"]
        assert len(indications) == 1
        assert "type 2 diabetes mellitus" in indications[0].text

    def test_metformin_extracts_dosage_section(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        dosage = [s for s in label.sections if s.loinc_code == "34068-7"]
        assert len(dosage) == 1

    def test_metformin_dosage_has_subsections(self):
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        dosage = [s for s in label.sections if s.loinc_code == "34068-7"][0]
        assert len(dosage.subsections) > 0
        titles = [s.title for s in dosage.subsections]
        assert any("Adult Dosage" in t for t in titles)

    def test_metformin_indications_text_is_clean(self):
        """Text should be stripped of XML markup — no tags, no linkHtml."""
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        indications = [s for s in label.sections if s.loinc_code == "34067-9"][0]
        assert "<" not in indications.text
        assert ">" not in indications.text

    def test_aspirin_parses_successfully(self):
        """OTC drug with different structure should also parse."""
        xml = (FIXTURES / "aspirin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        assert label.drug_name  # Should have a name
        assert label.set_id  # Should have a set_id

    def test_aspirin_has_target_sections(self):
        xml = (FIXTURES / "aspirin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        loinc_codes = {s.loinc_code for s in label.sections}
        # At least one of our target sections should be present
        assert loinc_codes & {"34067-9", "34068-7"}

    def test_extracts_both_target_sections(self):
        """Metformin should have both Indications and Dosage."""
        xml = (FIXTURES / "metformin_spl.xml").read_bytes()
        label = parse_spl_xml(xml)
        loinc_codes = {s.loinc_code for s in label.sections}
        assert "34067-9" in loinc_codes
        assert "34068-7" in loinc_codes


class TestMalformedXml:
    """Edge cases and error handling — P0 tests."""

    def test_completely_invalid_xml(self):
        with pytest.raises(ValueError, match="Malformed XML"):
            parse_spl_xml("not xml at all <<<>>>")

    def test_valid_xml_missing_drug_name(self):
        xml = """<?xml version="1.0"?>
        <document xmlns="urn:hl7-org:v3">
            <setId root="test-set-id"/>
            <versionNumber value="1"/>
            <component><structuredBody></structuredBody></component>
        </document>"""
        with pytest.raises(ValueError, match="drug name"):
            parse_spl_xml(xml)

    def test_valid_xml_missing_set_id(self):
        xml = """<?xml version="1.0"?>
        <document xmlns="urn:hl7-org:v3">
            <versionNumber value="1"/>
        </document>"""
        with pytest.raises(ValueError, match="setId"):
            parse_spl_xml(xml)

    def test_xml_with_no_target_sections(self):
        """Valid SPL XML with sections, but none matching our target LOINC codes."""
        xml = """<?xml version="1.0"?>
        <document xmlns="urn:hl7-org:v3">
            <setId root="test-set-id"/>
            <versionNumber value="1"/>
            <component>
                <structuredBody>
                    <component>
                        <section>
                            <code code="99999-9" codeSystem="2.16.840.1.113883.6.1"/>
                            <title>Some Other Section</title>
                            <text><paragraph>Irrelevant content.</paragraph></text>
                        </section>
                    </component>
                </structuredBody>
            </component>
        </document>"""
        # This would fail at drug name extraction since there's no manufacturedProduct
        with pytest.raises(ValueError, match="drug name"):
            parse_spl_xml(xml)

    def test_section_with_empty_text(self):
        """Section exists but has empty text element — should return empty string."""
        xml = """<?xml version="1.0"?>
        <document xmlns="urn:hl7-org:v3">
            <setId root="test-set-id"/>
            <versionNumber value="1"/>
            <author><assignedEntity><representedOrganization>
                <assignedEntity><assignedOrganization>
                    <assignedEntity><assignedOrganization>
                        <assignedEntity>
                            <performance><actDefinition><product>
                                <manufacturedProduct>
                                    <manufacturedProduct>
                                        <name>Test Drug</name>
                                    </manufacturedProduct>
                                </manufacturedProduct>
                            </product></actDefinition></performance>
                        </assignedEntity>
                    </assignedOrganization></assignedEntity>
                </assignedOrganization></assignedEntity>
            </representedOrganization></assignedEntity></author>
            <component>
                <structuredBody>
                    <component>
                        <section>
                            <code code="34067-9" codeSystem="2.16.840.1.113883.6.1"/>
                            <title>Indications</title>
                            <text></text>
                        </section>
                    </component>
                </structuredBody>
            </component>
        </document>"""
        label = parse_spl_xml(xml)
        indications = [s for s in label.sections if s.loinc_code == "34067-9"]
        assert len(indications) == 1
        assert indications[0].text == ""
