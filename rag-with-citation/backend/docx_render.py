from html import escape as html_escape
from pathlib import Path

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate

from storage import PAGE_HEIGHT_PT, PAGE_MARGIN_PT


def extract_docx_paragraphs(path: Path) -> list[tuple[int, str]]:
    doc = Document(str(path))
    out: list[tuple[int, str]] = []
    for i, para in enumerate(doc.paragraphs, start=1):
        text = (para.text or "").strip()
        if text:
            out.append((i, text))
    return out


class _PageTracker(Flowable):
    """Near-zero-height flowable that records page + PDF-coord Y at draw time."""

    def __init__(self, idx: int, mapping: dict[int, dict], end: bool = False):
        super().__init__()
        self.idx = idx
        self.mapping = mapping
        self.end = end

    def wrap(self, _availWidth, _availHeight):
        return 0.001, 0.001

    def draw(self):
        _, y_from_bottom = self.canv.absolutePosition(0, 0)
        # Convert to top-left origin (y measured from the top of the page).
        y_from_top = PAGE_HEIGHT_PT - y_from_bottom
        page = self.canv.getPageNumber()
        entry = self.mapping.setdefault(self.idx, {})
        if self.end:
            entry["bottom_page"] = page
            entry["bottom"] = y_from_top
        else:
            entry["top_page"] = page
            entry["top"] = y_from_top


def render_docx_to_pdf(
    paragraphs: list[tuple[int, str]], out_path: Path
) -> dict[int, dict]:
    """Render paragraphs to a PDF; return per-paragraph layout info."""
    mapping: dict[int, dict] = {}
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.leading = 15
    body.spaceAfter = 8
    body.fontSize = 11

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=PAGE_MARGIN_PT,
        rightMargin=PAGE_MARGIN_PT,
        topMargin=PAGE_MARGIN_PT,
        bottomMargin=PAGE_MARGIN_PT,
    )

    story: list = []
    for idx, text in paragraphs:
        story.append(_PageTracker(idx, mapping, end=False))
        story.append(Paragraph(html_escape(text), body))
        story.append(_PageTracker(idx, mapping, end=True))
    doc.build(story)
    return mapping


def docx_paragraph_payload(n: int, text: str, info: dict) -> dict:
    top_page = info.get("top_page", 1)
    bottom_page = info.get("bottom_page", top_page)
    top = info.get("top", PAGE_MARGIN_PT)
    # When a paragraph spans pages, the highlight band on the start page
    # extends to the bottom margin instead of the next page's coordinate.
    bottom = (
        info.get("bottom", top)
        if bottom_page == top_page
        else PAGE_HEIGHT_PT - PAGE_MARGIN_PT
    )
    return {
        "index": n,
        "text": text,
        "page": top_page,
        "top": top,
        "bottom": bottom,
    }
