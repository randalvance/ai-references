import os
import tempfile
import uuid
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pypdf import PdfReader

from simple_citation import get_citation_response

load_dotenv()

UPLOAD_DIR = Path(tempfile.gettempdir()) / "rag-with-citation-uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

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


def _pdf_path(pdf_id: str) -> Path:
    # Treat pdf_id as opaque; resolve and confirm it stays inside UPLOAD_DIR.
    candidate = (UPLOAD_DIR / f"{pdf_id}.pdf").resolve()
    if UPLOAD_DIR.resolve() not in candidate.parents:
        raise HTTPException(status_code=400, detail="Invalid pdf_id")
    return candidate


def _extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    chunks = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text:
            chunks.append(f"\n\nDocument (PDF Page {i + 1}):\n{text}")
    return "".join(chunks).strip()


@app.get("/api/health")
def health():
    return {"ok": True, "has_api_key": bool(os.getenv("ANTHROPIC_API_KEY"))}


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported")

    pdf_id = uuid.uuid4().hex
    dest = _pdf_path(pdf_id)
    contents = await file.read()
    dest.write_bytes(contents)
    return {"pdf_id": pdf_id, "url": f"/api/pdf/{pdf_id}"}


@app.get("/api/pdf/{pdf_id}")
def get_pdf(pdf_id: str):
    path = _pdf_path(pdf_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(str(path), media_type="application/pdf")


@app.post("/api/ask")
def ask(req: AskRequest):
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY is not set")

    path = _pdf_path(req.pdf_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF not found")
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    context = _extract_text(path)
    if not context:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    answer = get_citation_response(context, req.question)
    return {"answer": answer}
