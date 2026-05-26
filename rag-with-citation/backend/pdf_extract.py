from pathlib import Path
from typing import NamedTuple

import fitz  # PyMuPDF

from storage import PAGE_HEIGHT_PT, PAGE_WIDTH_PT


class PdfExtraction(NamedTuple):
    paragraphs: list[dict]
    page_width: float
    page_height: float


def extract_pdf_paragraphs(path: Path) -> PdfExtraction:
    """Extract paragraphs from a native PDF using PyMuPDF.

    Each paragraph has: index, text, page (1-based), left, right, top, bottom
    in PDF points with a top-left origin. Each column in a multi-column layout
    is a separate block (and therefore a separate paragraph index).
    """
    doc = fitz.open(str(path))
    paragraphs: list[dict] = []
    page_width = PAGE_WIDTH_PT
    page_height = PAGE_HEIGHT_PT
    idx = 0
    for page_idx, page in enumerate(doc, start=1):
        if page_idx == 1:
            page_width = page.rect.width
            page_height = page.rect.height
        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:  # 0 = text block; skip images / drawings
                continue
            text = " ".join(
                span["text"]
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            ).strip()
            if not text:
                continue
            x0, y0, x1, y1 = block["bbox"]
            idx += 1
            paragraphs.append({
                "index": idx,
                "text": text,
                "page": page_idx,
                "left": x0,
                "right": x1,
                "top": y0,
                "bottom": y1,
            })
    doc.close()
    return PdfExtraction(paragraphs, page_width, page_height)
