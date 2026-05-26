import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from docx_render import (
    docx_paragraph_payload,
    extract_docx_paragraphs,
    render_docx_to_pdf,
)
from pdf_extract import extract_pdf_paragraphs
from simple_citation import get_citation_response
from storage import (
    PAGE_HEIGHT_PT,
    PAGE_WIDTH_PT,
    SUPPORTED_EXTS,
    UPLOAD_DIR,
    DocKind,
    pdf_path,
    source_path,
    validate_doc_id,
)

load_dotenv()

app = FastAPI(title="RAG with Citation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Extracted paragraphs keyed by doc_id, populated on upload. /api/ask re-extracts
# on cache miss so that uploads survive a server restart (the files in UPLOAD_DIR
# outlive the process; the cache does not).
_paragraph_cache: dict[str, list[dict]] = {}


class AskRequest(BaseModel):
    doc_id: str
    question: str


def _resolve_doc(doc_id: str) -> tuple[Path, DocKind]:
    try:
        validate_doc_id(doc_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    found = source_path(doc_id)
    if not found:
        raise HTTPException(status_code=404, detail="Document not found")
    return found


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
    doc_id = uuid.uuid4().hex
    source = UPLOAD_DIR / f"{doc_id}{ext}"
    source.write_bytes(await file.read())

    response: dict = {"doc_id": doc_id, "kind": kind, "url": f"/api/pdf/{doc_id}"}
    if kind == "pdf":
        pdf_dest = pdf_path(doc_id)
        if source != pdf_dest:
            pdf_dest.write_bytes(source.read_bytes())
        extraction = extract_pdf_paragraphs(pdf_dest)
        response["page_width"] = extraction.page_width
        response["page_height"] = extraction.page_height
        response["paragraphs"] = extraction.paragraphs
    else:
        docx_paragraphs = extract_docx_paragraphs(source)
        layout = render_docx_to_pdf(docx_paragraphs, pdf_path(doc_id))
        response["page_width"] = PAGE_WIDTH_PT
        response["page_height"] = PAGE_HEIGHT_PT
        response["paragraphs"] = [
            docx_paragraph_payload(n, t, layout.get(n, {}))
            for n, t in docx_paragraphs
        ]
    _paragraph_cache[doc_id] = response["paragraphs"]
    return response


@app.get("/api/pdf/{doc_id}")
def get_pdf(doc_id: str):
    _resolve_doc(doc_id)
    pdf = pdf_path(doc_id)
    if not pdf.exists():
        raise HTTPException(status_code=404, detail="Rendered PDF not found")
    return FileResponse(str(pdf), media_type="application/pdf")


def _paragraphs_or_reindex(doc_id: str, source: Path, kind: DocKind) -> list[dict]:
    cached = _paragraph_cache.get(doc_id)
    if cached is not None:
        return cached
    if kind == "pdf":
        paragraphs = extract_pdf_paragraphs(pdf_path(doc_id)).paragraphs
    else:
        paragraphs = [{"index": n, "text": t} for n, t in extract_docx_paragraphs(source)]
    _paragraph_cache[doc_id] = paragraphs
    return paragraphs


@app.post("/api/ask")
def ask(req: AskRequest):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set")
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    source, kind = _resolve_doc(req.doc_id)
    paragraphs = _paragraphs_or_reindex(req.doc_id, source, kind)
    context = _build_context(paragraphs).strip()
    if not context:
        raise HTTPException(status_code=400, detail="Could not extract text from document")

    answer = get_citation_response(context, req.question)
    return {"answer": answer, "kind": kind}
