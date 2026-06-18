"""Extract text from uploaded files."""

from io import BytesIO

from pypdf import PdfReader
from docx import Document

from app.core.logging import get_logger

log = get_logger(__name__)


def extract_text(filename: str, content: bytes) -> str:
    """Extract text from a file based on its extension.

    Args:
        filename: Name of the file (used to determine type).
        content: Raw file bytes.

    Returns:
        Extracted text.

    Raises:
        ValueError: If the file type is not supported.
    """
    name_lower = filename.lower()

    if name_lower.endswith(".txt"):
        return content.decode("utf-8", errors="replace")

    if name_lower.endswith(".pdf"):
        try:
            pdf = PdfReader(BytesIO(content))
            text_parts = []
            for page in pdf.pages:
                text_parts.append(page.extract_text())
            return "\n".join(text_parts)
        except Exception as e:
            log.error("Failed to extract text from PDF %s: %s", filename, e)
            raise ValueError(f"Failed to parse PDF: {e}") from e

    if name_lower.endswith(".docx"):
        try:
            doc = Document(BytesIO(content))
            text_parts = []
            for paragraph in doc.paragraphs:
                text_parts.append(paragraph.text)
            return "\n".join(text_parts)
        except Exception as e:
            log.error("Failed to extract text from DOCX %s: %s", filename, e)
            raise ValueError(f"Failed to parse DOCX: {e}") from e

    raise ValueError(f"Unsupported file type: {filename}")
