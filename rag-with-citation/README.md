# RAG with Citation

An implementation reference for answering questions about a **PDF or Word document** with clickable citations that jump the viewer to the cited paragraph.

Built as a small full-stack app:

- **Frontend** — React + Vite + `react-pdf` (port `5173`)
- **Backend** — FastAPI (port `8000`)
- **LLM** — Anthropic Claude via `langchain-anthropic`

A single root command boots both servers.

## How citations work

Citations are paragraph-level for both formats. `.docx` files have no real page boundaries, so the backend renders the DOCX into a PDF (via ReportLab) and records where each paragraph lands. Native PDFs are parsed with PyMuPDF, which gives the bounding box of each text block directly.

1. The backend extracts text, labelling each chunk with its paragraph index, and records the page + top/bottom Y in PDF points.
2. The system prompt instructs the model to cite the source inline as `[[para:N]]`.
3. The frontend parses the model's answer, renders each `[[para:N]]` as a clickable link, and on click jumps `react-pdf` to the matching page and overlays a highlight band on that paragraph's coordinates.

The model is instructed to answer **only** from the provided context and to say it does not know when the answer isn't there.

## Project layout

```
backend/
  main.py              FastAPI app + endpoints
  storage.py           Upload paths, doc-kind detection, page constants
  pdf_extract.py       Native PDF -> paragraphs (PyMuPDF)
  docx_render.py       DOCX -> rendered PDF + per-paragraph layout
  simple_citation.py   Claude prompt + chain
frontend/
  src/App.jsx                          Composition + top-level state
  src/components/UploadAndAsk.jsx      Upload, question, answer panel
  src/components/AnswerWithCitations.jsx
  src/components/PdfViewer.jsx         react-pdf viewer + highlight band
  src/lib/api.js                       /api wrappers, snake_case -> camelCase
  src/lib/parseCitations.js            [[para:N]] parser
  src/lib/computeHighlightBand.js      Paragraph coords -> canvas px
  src/App.css
  vite.config.js       Dev-server proxy /api -> 127.0.0.1:8000
  index.html
package.json           Root orchestration (concurrently)
requirements.txt       Python deps
.env.example           Template for ANTHROPIC_API_KEY
```

## Prerequisites

- Node 18+
- Python 3.9+
- An Anthropic API key

## Setup

```bash
cp .env.example .env       # then set ANTHROPIC_API_KEY=...

python3 -m venv .venv      # if .venv doesn't already exist
npm run install:all        # installs root npm deps, frontend npm deps, and Python deps into .venv
```

`install:all` runs:

```
npm install
npm --prefix frontend install
./.venv/bin/pip install -r requirements.txt
```

## Run

```bash
npm run dev      # or: npm start
```

Both commands are equivalent and launch the backend (`uvicorn --reload`) and the frontend (`vite`) together via `concurrently`. Open:

> http://localhost:5173

The Vite dev server proxies `/api/*` to FastAPI, so the browser only talks to `5173`.

## API reference

All endpoints are JSON unless noted. Errors return `{"detail": "..."}` with appropriate status codes.

| Method | Path                | Body / Params                                          | Returns                                                                |
|--------|---------------------|--------------------------------------------------------|------------------------------------------------------------------------|
| GET    | `/api/health`       | —                                                      | `{ok, has_api_key}`                                                    |
| POST   | `/api/upload`       | `multipart/form-data` with `file=<.pdf or .docx>`      | `{doc_id, kind, url, page_width, page_height, paragraphs[]}`           |
| GET    | `/api/pdf/{doc_id}` | path param                                             | `application/pdf` stream (native PDF or DOCX-rendered PDF)             |
| POST   | `/api/ask`          | `{doc_id, question}`                                   | `{answer, kind}` with inline `[[para:N]]`                              |

Each entry in `paragraphs[]` has `{index, text, page, top, bottom}` in PDF points (top-left origin). Extracted paragraphs are cached in-process and re-extracted on demand after a server restart.

Example:

```bash
ID=$(curl -s -F "file=@example.pdf" http://localhost:8000/api/upload | jq -r .doc_id)
curl -s http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d "{\"doc_id\":\"$ID\",\"question\":\"Summarise section 2.\"}"
```

## Troubleshooting

- **`ANTHROPIC_API_KEY is not set`** — `.env` is loaded by the backend on startup; restart `npm run dev` after editing it.
- **Port already in use** — kill leftover processes: `lsof -ti:8000,5173 | xargs kill -9`.
- **PDF text is empty** — scanned/image-only PDFs have no extractable text; OCR them first.
- **DOCX has no `.docx` extension** — only `.docx` is supported; legacy `.doc` files need to be re-saved or converted first.
- **Citations don't appear** — the model only cites sources it actually used; if the answer doesn't reference the document, no citations will render.
