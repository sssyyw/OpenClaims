"""Parse DailyMed SPL XML files to extract drug labels.

SPL (Structured Product Labeling) is the HL7 v3 XML format used by FDA/DailyMed.
This parser extracts drug name, setId, and label section text from SPL XML files.

Key LOINC codes:
  34067-9  Indications & Usage
  34068-7  Dosage & Administration
"""

from dataclasses import dataclass, field
from lxml import etree

NS = {"hl7": "urn:hl7-org:v3"}

# Sections to extract for POC — expand incrementally
TARGET_SECTIONS: dict[str, str] = {
    "34067-9": "Indications and Usage",
    "34068-7": "Dosage and Administration",
}


@dataclass
class ParsedSection:
    loinc_code: str
    title: str
    display_name: str
    text: str
    subsections: list["ParsedSection"] = field(default_factory=list)


@dataclass
class ParsedLabel:
    drug_name: str
    set_id: str
    version: str
    manufacturer: str
    sections: list[ParsedSection]


def parse_spl_xml(xml_content: str | bytes) -> ParsedLabel:
    """Parse an SPL XML document and extract target sections.

    Args:
        xml_content: Raw XML string or bytes.

    Returns:
        ParsedLabel with drug name, set_id, and extracted sections.

    Raises:
        ValueError: If the XML is malformed or missing required fields.
    """
    try:
        if isinstance(xml_content, str):
            xml_content = xml_content.encode("utf-8")
        root = etree.fromstring(xml_content)
    except etree.XMLSyntaxError as e:
        raise ValueError(f"Malformed XML: {e}") from e

    set_id = _extract_set_id(root)
    drug_name = _extract_drug_name(root)
    version = _extract_version(root)
    manufacturer = _extract_manufacturer(root)
    sections = _extract_sections(root)

    return ParsedLabel(
        drug_name=drug_name,
        set_id=set_id,
        version=version,
        manufacturer=manufacturer,
        sections=sections,
    )


def _extract_drug_name(root: etree._Element) -> str:
    """Extract drug name from manufacturedProduct/manufacturedProduct/name."""
    # Primary: manufactured product name
    name_el = root.find(
        ".//hl7:manufacturedProduct/hl7:manufacturedProduct/hl7:name", NS
    )
    if name_el is not None and name_el.text:
        return name_el.text.strip()

    # Fallback: generic medicine name
    name_el = root.find(
        ".//hl7:genericMedicine/hl7:name", NS
    )
    if name_el is not None and name_el.text:
        return name_el.text.strip()

    raise ValueError("Could not find drug name in SPL XML")


def _extract_set_id(root: etree._Element) -> str:
    """Extract setId UUID from document/setId/@root."""
    set_id_el = root.find("hl7:setId", NS)
    if set_id_el is not None:
        return set_id_el.get("root", "")
    raise ValueError("Could not find setId in SPL XML")


def _extract_version(root: etree._Element) -> str:
    """Extract version number from document/versionNumber/@value."""
    version_el = root.find("hl7:versionNumber", NS)
    if version_el is not None:
        return version_el.get("value", "")
    return ""


def _extract_manufacturer(root: etree._Element) -> str:
    """Extract manufacturer name from representedOrganization/name."""
    org = root.find(".//hl7:representedOrganization/hl7:name", NS)
    if org is not None and org.text:
        return org.text.strip()
    return ""


def _extract_sections(root: etree._Element) -> list[ParsedSection]:
    """Find and extract target sections by LOINC code."""
    sections = []

    # Sections are at: document/component/structuredBody/component/section
    for section_el in root.iterfind(
        ".//hl7:component/hl7:structuredBody/hl7:component/hl7:section", NS
    ):
        parsed = _try_parse_section(section_el)
        if parsed is not None:
            sections.append(parsed)

    return sections


def _try_parse_section(section_el: etree._Element) -> ParsedSection | None:
    """Parse a section element if its LOINC code is in TARGET_SECTIONS."""
    code_el = section_el.find("hl7:code", NS)
    if code_el is None:
        return None

    loinc_code = code_el.get("code", "")
    if loinc_code not in TARGET_SECTIONS:
        return None

    title_el = section_el.find("hl7:title", NS)
    title = _get_text_content(title_el) if title_el is not None else ""

    display_name = TARGET_SECTIONS[loinc_code]

    # Extract text from the section's <text> element
    text = _extract_section_text(section_el)

    # Extract subsections (section/component/section)
    subsections = _extract_subsections(section_el)

    return ParsedSection(
        loinc_code=loinc_code,
        title=title.strip(),
        display_name=display_name,
        text=text.strip(),
        subsections=subsections,
    )


def _extract_subsections(section_el: etree._Element) -> list[ParsedSection]:
    """Extract nested subsections from component/section elements."""
    subsections = []
    for comp in section_el.iterfind("hl7:component/hl7:section", NS):
        code_el = comp.find("hl7:code", NS)
        loinc_code = code_el.get("code", "") if code_el is not None else ""

        title_el = comp.find("hl7:title", NS)
        title = _get_text_content(title_el) if title_el is not None else ""

        text = _extract_section_text(comp)

        subsections.append(ParsedSection(
            loinc_code=loinc_code,
            title=title.strip(),
            display_name=title.strip(),
            text=text.strip(),
            subsections=[],  # Don't recurse deeper for POC
        ))
    return subsections


def _extract_section_text(section_el: etree._Element) -> str:
    """Extract all text content from a section's <text> element.

    Strips XML markup (content, linkHtml, sup, br, etc.) and returns plain text.
    Handles paragraphs, lists, and tables.
    """
    text_el = section_el.find("hl7:text", NS)
    if text_el is None:
        return ""
    return _get_text_content(text_el)


def _get_text_content(element: etree._Element) -> str:
    """Recursively extract all text content from an element, stripping markup."""
    parts = []
    if element.text:
        parts.append(element.text)
    for child in element:
        tag = etree.QName(child.tag).localname if isinstance(child.tag, str) else ""
        if tag == "br":
            parts.append("\n")
        elif tag == "paragraph":
            child_text = _get_text_content(child).strip()
            if child_text:
                parts.append(child_text)
                parts.append("\n")
        elif tag == "item":
            child_text = _get_text_content(child).strip()
            if child_text:
                parts.append(f"- {child_text}\n")
        elif tag in ("linkHtml", "sup", "sub"):
            # Include the text but don't add extra formatting
            child_text = _get_text_content(child)
            if child_text:
                parts.append(child_text.strip())
        else:
            parts.append(_get_text_content(child))
        if child.tail:
            parts.append(child.tail)
    return "".join(parts)
