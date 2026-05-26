import tempfile
from pathlib import Path
from typing import Literal

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

UPLOAD_DIR = Path(tempfile.gettempdir()) / "rag-with-citation-uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DocKind = Literal["pdf", "docx"]
SUPPORTED_EXTS: dict[str, DocKind] = {".pdf": "pdf", ".docx": "docx"}

PAGE_WIDTH_PT, PAGE_HEIGHT_PT = letter
PAGE_MARGIN_PT = 0.75 * inch


def validate_doc_id(doc_id: str) -> None:
    if not doc_id or "/" in doc_id or "\\" in doc_id or ".." in doc_id:
        raise ValueError("Invalid id")


def source_path(doc_id: str) -> tuple[Path, DocKind] | None:
    """Return the uploaded source file and its kind, or None if not found."""
    for ext, kind in SUPPORTED_EXTS.items():
        candidate = UPLOAD_DIR / f"{doc_id}{ext}"
        if candidate.exists():
            return candidate, kind
    return None


def pdf_path(doc_id: str) -> Path:
    """Path of the PDF served to the viewer (native PDF, or DOCX-converted PDF)."""
    return UPLOAD_DIR / f"{doc_id}.pdf"
