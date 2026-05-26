import os
import tempfile
import uuid
from html import escape as html_escape
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF
from docx import Document
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate

from simple_citation import get_citation_response

load_dotenv()

UPLOAD_DIR = Path(tempfile.gettempdir()) / "rag-with-citation-uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

DocKind = Literal["pdf", "docx"]
SUPPORTED_EXTS: dict[str, DocKind] = {".pdf": "pdf", ".docx": "docx"}

PAGE_WIDTH_PT, PAGE_HEIGHT_PT = letter
PAGE_MARGIN_PT = 0.75 * inch

app = FastAPI(title="RAG with Citation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    pdf_id: str
    question: str


def _source_path(pdf_id: str) -> tuple[Path, DocKind]:
    if not pdf_id or "/" in pdf_id or "\\" in pdf_id or ".." in pdf_id:
        raise HTTPException(status_code=400, detail="Invalid id")
    for ext, kind in SUPPORTED_EXTS.items():
        candidate = UPLOAD_DIR / f"{pdf_id}{ext}"
        if candidate.exists():
            return candidate, kind
    raise HTTPException(status_code=404, detail="Document not found")


def _pdf_path(pdf_id: str) -> Path:
    """Path of the PDF served to the viewer (native PDF, or DOCX-converted PDF)."""
    return UPLOAD_DIR / f"{pdf_id}.pdf"


# -------- DOCX -> rendered PDF + paragraph layout --------


def _extract_docx_paragraphs(path: Path) -> list[tuple[int, str]]:
    doc = Document(str(path))
    out: list[tuple[int, str]] = []
    for i, para in enumerate(doc.paragraphs, start=1):
        text = (para.text or "").strip()
        if text:
            out.append((i, text))
    return out


class _PageTracker(Flowable):
    """Zero-height flowable that records the page + PDF-coord Y at draw time."""

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


def _render_docx_to_pdf(
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


def _docx_paragraph_payload(n: int, text: str, info: dict) -> dict:
    top_page = info.get("top_page", 1)
    bottom_page = info.get("bottom_page", top_page)
    top = info.get("top", PAGE_MARGIN_PT)
    bottom = (
        info.get("bottom", top)
        if bottom_page == top_page
        else PAGE_HEIGHT_PT - PAGE_MARGIN_PT  # band extends to bottom margin on the start page
    )
    return {
        "index": n,
        "text": text,
        "page": top_page,
        "top": top,
        "bottom": bottom,
    }


# -------- Native PDF -> paragraph extraction with bboxes --------


def _extract_pdf_paragraphs(path: Path) -> tuple[list[dict], float, float]:
    """Extract paragraphs from a native PDF using PyMuPDF.

    Returns (paragraphs, page_width, page_height). Each paragraph has:
        index, text, page (1-based), top, bottom (PDF points, top-left origin).
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
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            if block.get("type") != 0:  # 0 = text block; skip images / drawings
                continue
            text = " ".join(
                span["text"]
                for line in block.get("lines", [])
                for span in line.get("spans", [])
            ).strip()
            if not text:
                continue
            _, y0, _, y1 = block["bbox"]
            idx += 1
            paragraphs.append(
                {
                    "index": idx,
                    "text": text,
                    "page": page_idx,
                    "top": y0,
                    "bottom": y1,
                }
            )
    doc.close()
    return paragraphs, page_width, page_height


# -------- Context builders + endpoints --------


def _build_context(paragraphs: list[dict]) -> str:
    return "\n\n".join(
        f"Document (Paragraph {p['index']}):\n{p['text']}" for p in paragraphs
    )


@app.get("/api/health")
def health():
    return {"ok": True, "has_api_key": bool(os.getenv("ANTHROPIC_API_KEY"))}


@app.post("/api/upload")
async def upload_doc(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(status_code=400, detail="Only .pdf and .docx are supported")

    kind = SUPPORTED_EXTS[ext]
    pdf_id = uuid.uuid4().hex
    source = UPLOAD_DIR / f"{pdf_id}{ext}"
    source.write_bytes(await file.read())

    response: dict = {"pdf_id": pdf_id, "kind": kind, "url": f"/api/pdf/{pdf_id}"}
    if kind == "pdf":
        pdf_dest = _pdf_path(pdf_id)
        if source != pdf_dest:
            pdf_dest.write_bytes(source.read_bytes())
        paragraphs, page_width, page_height = _extract_pdf_paragraphs(pdf_dest)
        response["page_width"] = page_width
        response["page_height"] = page_height
        response["paragraphs"] = paragraphs
    else:
        docx_paragraphs = _extract_docx_paragraphs(source)
        layout = _render_docx_to_pdf(docx_paragraphs, _pdf_path(pdf_id))
        response["page_width"] = PAGE_WIDTH_PT
        response["page_height"] = PAGE_HEIGHT_PT
        response["paragraphs"] = [
            _docx_paragraph_payload(n, t, layout.get(n, {}))
            for n, t in docx_paragraphs
        ]
    return response


@app.get("/api/pdf/{pdf_id}")
def get_pdf(pdf_id: str):
    _source_path(pdf_id)
    pdf = _pdf_path(pdf_id)
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="Rendered PDF not found")
    return FileResponse(str(pdf), media_type="application/pdf")


def _paragraphs_for(source: Path, kind: DocKind, pdf_id: str) -> list[dict]:
    """Re-extract paragraphs for /api/ask. Only (index, text) are used downstream."""
    if kind == "pdf":
        paragraphs, _, _ = _extract_pdf_paragraphs(_pdf_path(pdf_id))
        return paragraphs
    return [
        {"index": n, "text": t} for n, t in _extract_docx_paragraphs(source)
    ]


@app.post("/api/ask")
def ask(req: AskRequest):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set")
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    source, kind = _source_path(req.pdf_id)
    paragraphs = _paragraphs_for(source, kind, req.pdf_id)
    context = _build_context(paragraphs).strip()
    if not context:
        raise HTTPException(status_code=400, detail="Could not extract text from document")

    answer = get_citation_response(context, req.question)
    return {"answer": answer, "kind": kind}
