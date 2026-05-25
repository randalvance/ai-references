# RAG with Citation

An implementation reference for answering questions about a PDF with **clickable page citations** that jump the embedded PDF viewer to the cited page.

Built as a small full-stack app:

- **Frontend** — React + Vite (port `5173`)
- **Backend** — FastAPI (port `8000`)
- **LLM** — Anthropic Claude via `langchain-anthropic`

A single root command boots both servers.

## How citations work

1. The user uploads a PDF. The backend extracts text page-by-page, labelling each chunk with its source page number.
2. The system prompt instructs the model to cite the source page inline using the format `[[page:N]]` whenever it uses information from the PDF.
3. The frontend parses the model's answer, replaces each `[[page:N]]` token with a clickable link, and rewrites the embedded PDF iframe's `src` to `#page=N` when clicked — so the viewer jumps to that page.

The model is instructed to answer **only** from the provided context and to say it does not know when the answer isn't there.

## Project layout

```
backend/
  main.py              FastAPI app + endpoints
  simple_citation.py   Claude prompt + chain (also runnable as CLI)
frontend/
  src/App.jsx          UI: upload, ask, render answer w/ citations, PDF iframe
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

## CLI sanity check

Run the citation chain end-to-end without the UI:

```bash
./.venv/bin/python backend/simple_citation.py
```

Uses a hardcoded set of mini-documents and prints the model's cited answer.

## API reference

All endpoints are JSON unless noted. Errors return `{"detail": "..."}` with appropriate status codes.

| Method | Path                | Body / Params                                  | Returns                              |
|--------|---------------------|------------------------------------------------|--------------------------------------|
| GET    | `/api/health`       | —                                              | `{ok, has_api_key}`                  |
| POST   | `/api/upload`       | `multipart/form-data` with `file=<pdf>`        | `{pdf_id, url}`                      |
| GET    | `/api/pdf/{id}`     | path param                                     | `application/pdf` stream             |
| POST   | `/api/ask`          | `{pdf_id, question}`                           | `{answer}` (with inline `[[page:N]]`) |

Example:

```bash
PDF_ID=$(curl -s -F "file=@example.pdf" http://localhost:8000/api/upload | jq -r .pdf_id)
curl -s http://localhost:8000/api/ask \
  -H 'Content-Type: application/json' \
  -d "{\"pdf_id\":\"$PDF_ID\",\"question\":\"Summarise section 2.\"}"
```

## Troubleshooting

- **`ANTHROPIC_API_KEY is not set`** — `.env` is loaded by the backend on startup; restart `npm run dev` after editing it.
- **Port already in use** — kill leftover processes: `lsof -ti:8000,5173 | xargs kill -9`.
- **PDF text is empty** — scanned/image-only PDFs have no extractable text; OCR them first.
- **Citations don't appear** — the model only cites pages it actually used; if the answer doesn't reference the PDF, no citations will render.
