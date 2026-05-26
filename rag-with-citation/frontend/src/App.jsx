import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

function renderAnswer(text, onCitationClick) {
  const parts = []
  const regex = /\[\[(page|para):(\d+)\]\]/g
  let lastIndex = 0
  let match
  let key = 0
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<span key={key++}>{text.slice(lastIndex, match.index)}</span>)
    }
    const type = match[1]
    const n = Number(match[2])
    const label = type === 'page' ? `Page ${n}` : `¶ ${n}`
    parts.push(
      <a
        key={key++}
        href="#"
        className="citation"
        onClick={(e) => {
          e.preventDefault()
          onCitationClick(type, n)
        }}
      >
        [{label}]
      </a>,
    )
    lastIndex = regex.lastIndex
  }
  if (lastIndex < text.length) {
    parts.push(<span key={key++}>{text.slice(lastIndex)}</span>)
  }
  return parts
}

function escapeHtml(s) {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export default function App() {
  const [doc, setDoc] = useState(null) // { id, kind, url, paragraphs? }
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [asking, setAsking] = useState(false)
  const [page, setPage] = useState(1)
  const [numPages, setNumPages] = useState(0)
  const [highlightPara, setHighlightPara] = useState(null)
  const [pageWidth, setPageWidth] = useState(800)
  const viewerRef = useRef(null)

  useEffect(() => {
    const el = viewerRef.current
    if (!el) return
    const update = () => setPageWidth(Math.max(320, el.clientWidth - 24))
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [doc])

  const highlightParaText = useMemo(() => {
    if (!highlightPara || !doc?.paragraphs) return null
    return doc.paragraphs.find((p) => p.index === highlightPara)?.text || null
  }, [highlightPara, doc])

  const textRenderer = useCallback(
    (item) => {
      const str = item.str
      if (!highlightParaText || !str || !str.trim()) return escapeHtml(str)
      // Wrap the span if its text is a slice of the highlighted paragraph.
      // Reportlab renders one text item per line, so each item.str is
      // typically a continuous substring of the paragraph's text.
      const trimmed = str.trim()
      if (trimmed.length >= 2 && highlightParaText.includes(trimmed)) {
        return `<mark class="para-highlight">${escapeHtml(str)}</mark>`
      }
      return escapeHtml(str)
    },
    [highlightParaText],
  )

  async function handleUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setAnswer('')
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/upload', { method: 'POST', body: form })
      if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed')
      const data = await res.json()
      setDoc({
        id: data.pdf_id,
        kind: data.kind,
        url: data.url,
        paragraphs: data.paragraphs,
      })
      setPage(1)
      setNumPages(0)
      setHighlightPara(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  async function handleAsk() {
    if (!doc) {
      setError('Upload a document first.')
      return
    }
    if (!question.trim()) {
      setError('Enter a question.')
      return
    }
    setError('')
    setAnswer('')
    setAsking(true)
    try {
      const res = await fetch('/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pdf_id: doc.id, question }),
      })
      if (!res.ok) throw new Error((await res.json()).detail || 'Request failed')
      const data = await res.json()
      setAnswer(data.answer)
    } catch (err) {
      setError(err.message)
    } finally {
      setAsking(false)
    }
  }

  function handleCitationClick(type, n) {
    if (type === 'page') {
      const target = numPages ? Math.min(Math.max(1, n), numPages) : Math.max(1, n)
      setPage(target)
      setHighlightPara(null)
      return
    }
    // paragraph citation — map to page via doc.paragraphs
    const para = doc?.paragraphs?.find((p) => p.index === n)
    if (para?.page) {
      setPage(numPages ? Math.min(Math.max(1, para.page), numPages) : para.page)
    }
    setHighlightPara(n)
  }

  return (
    <div className="app">
      <header>
        <h1>AI Citation Reference</h1>
        <p>Upload a PDF or Word document and ask questions. Click citations to jump to the source.</p>
      </header>

      <div className="grid">
        <section className="panel">
          <label className="file-input">
            <input
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleUpload}
              disabled={uploading}
            />
            <span>{uploading ? 'Uploading…' : doc ? 'Replace document' : 'Upload PDF or DOCX'}</span>
          </label>

          <textarea
            placeholder="Ask a question about the document…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={4}
          />

          <button onClick={handleAsk} disabled={asking || !doc}>
            {asking ? 'Thinking…' : 'Get Answer'}
          </button>

          {error && <div className="error">{error}</div>}

          {answer && (
            <div className="answer">{renderAnswer(answer, handleCitationClick)}</div>
          )}
        </section>

        <section className="panel viewer" ref={viewerRef}>
          {!doc && <div className="placeholder">Document preview will appear here.</div>}

          {doc && (
            <div className="pdf-view">
              <div className="pdf-controls">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                >
                  Prev
                </button>
                <span className="pdf-page-label">
                  Page {page}
                  {numPages ? ` of ${numPages}` : ''}
                </span>
                <button
                  onClick={() => setPage((p) => (numPages ? Math.min(numPages, p + 1) : p + 1))}
                  disabled={numPages > 0 && page >= numPages}
                >
                  Next
                </button>
              </div>
              <div className="pdf-canvas-wrap">
                <Document
                  file={doc.url}
                  onLoadSuccess={({ numPages: n }) => setNumPages(n)}
                  onLoadError={(err) => setError(`Failed to load PDF: ${err.message}`)}
                  loading={<div className="placeholder">Loading PDF…</div>}
                >
                  <Page
                    pageNumber={page}
                    width={pageWidth}
                    renderAnnotationLayer={false}
                    renderTextLayer={true}
                    customTextRenderer={textRenderer}
                  />
                </Document>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
