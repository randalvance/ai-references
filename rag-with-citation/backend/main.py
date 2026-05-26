import os
import tempfile
import uuid
from html import escape as html_escape
from pathlib import Path
from typing import Literal

from docx import Document
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader
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
    # Rendered/served PDF — same name for native PDFs and DOCX-converted ones.
    return UPLOAD_DIR / f"{pdf_id}.pdf"


def _extract_pdf_pages(path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    out: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            out.append((i, text))
    return out


def _extract_docx_paragraphs(path: Path) -> list[tuple[int, str]]:
    doc = Document(str(path))
    out: list[tuple[int, str]] = []
    for i, para in enumerate(doc.paragraphs, start=1):
        text = (para.text or "").strip()
        if text:
            out.append((i, text))
    return out


class _PageTracker(Flowable):
    """Zero-height flowable that records the page it draws on."""

    def __init__(self, idx: int, mapping: dict[int, int]):
        super().__init__()
        self.idx = idx
        self.mapping = mapping

    def wrap(self, _availWidth, _availHeight):
        return 0.001, 0.001

    def draw(self):
        self.mapping[self.idx] = self.canv.getPageNumber()


def _render_docx_to_pdf(
    paragraphs: list[tuple[int, str]], out_path: Path
) -> dict[int, int]:
    """Render paragraphs to a PDF; return {paragraph_index: starting_page}."""
    mapping: dict[int, int] = {}
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    body.leading = 15
    body.spaceAfter = 8
    body.fontSize = 11

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    story: list = []
    for idx, text in paragraphs:
        story.append(_PageTracker(idx, mapping))
        story.append(Paragraph(html_escape(text), body))
    doc.build(story)
    return mapping


def _build_context(kind: DocKind, path: Path) -> str:
    if kind == "pdf":
        chunks = _extract_pdf_pages(path)
        return "\n\n".join(f"Document (PDF Page {n}):\n{t}" for n, t in chunks)
    chunks = _extract_docx_paragraphs(path)
    return "\n\n".join(f"Document (Paragraph {n}):\n{t}" for n, t in chunks)


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
        # Native PDF — served directly.
        pdf_dest = _pdf_path(pdf_id)
        if source != pdf_dest:
            pdf_dest.write_bytes(source.read_bytes())
    else:
        paragraphs = _extract_docx_paragraphs(source)
        page_map = _render_docx_to_pdf(paragraphs, _pdf_path(pdf_id))
        response["paragraphs"] = [
            {"index": n, "text": t, "page": page_map.get(n, 1)}
            for n, t in paragraphs
        ]
    return response


@app.get("/api/pdf/{pdf_id}")
def get_pdf(pdf_id: str):
    _source_path(pdf_id)  # validate id + existence
    pdf = _pdf_path(pdf_id)
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="Rendered PDF not found")
    return FileResponse(str(pdf), media_type="application/pdf")


@app.post("/api/ask")
def ask(req: AskRequest):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set")
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    path, kind = _source_path(req.pdf_id)
    context = _build_context(kind, path).strip()
    if not context:
        raise HTTPException(status_code=400, detail="Could not extract text from document")

    answer = get_citation_response(context, req.question, kind=kind)
    return {"answer": answer, "kind": kind}
