"""Document text extraction for promotional materials.

Supports PDF (PyMuPDF) and DOCX (python-docx).
Returns plain text for downstream claim extraction by the LLM.
"""

import io

import fitz  # PyMuPDF
from docx import Document


class UnsupportedFormatError(Exception):
    pass


class DocumentParseError(Exception):
    pass


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from a document based on file extension.

    Args:
        file_bytes: Raw file content.
        filename: Original filename (used to determine format).

    Returns:
        Extracted plain text.

    Raises:
        UnsupportedFormatError: If the file format is not supported.
        DocumentParseError: If the file is corrupted or unreadable.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        return extract_pdf(file_bytes)
    elif ext == "docx":
        return extract_docx(file_bytes)
    else:
        raise UnsupportedFormatError(
            f"Unsupported format: .{ext}. Upload a PDF or DOCX file."
        )


def extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF using PyMuPDF.

    Raises DocumentParseError for corrupted/encrypted/empty PDFs.
    """
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise DocumentParseError(f"Could not open PDF: {e}") from e

    if doc.is_encrypted:
        doc.close()
        raise DocumentParseError("PDF is encrypted. Please upload an unencrypted file.")

    pages = []
    for page in doc:
        text = page.get_text()
        if text.strip():
            pages.append(text.strip())
    doc.close()

    if not pages:
        raise DocumentParseError("PDF has no extractable text. It may be image-only.")

    return "\n\n".join(pages)


def extract_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX using python-docx.

    Raises DocumentParseError for corrupted files.
    """
    try:
        doc = Document(io.BytesIO(file_bytes))
    except Exception as e:
        raise DocumentParseError(f"Could not open DOCX: {e}") from e

    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    if not paragraphs:
        raise DocumentParseError("DOCX has no text content.")

    return "\n\n".join(paragraphs)
