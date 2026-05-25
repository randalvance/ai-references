import { useMemo, useRef, useState } from 'react'

function renderAnswer(text, onCitationClick) {
  const parts = []
  const regex = /\[\[page:(\d+)\]\]/g
  let lastIndex = 0
  let match
  let key = 0
  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<span key={key++}>{text.slice(lastIndex, match.index)}</span>)
    }
    const page = match[1]
    parts.push(
      <a
        key={key++}
        href="#"
        className="citation"
        onClick={(e) => {
          e.preventDefault()
          onCitationClick(Number(page))
        }}
      >
        [Page {page}]
      </a>,
    )
    lastIndex = regex.lastIndex
  }
  if (lastIndex < text.length) {
    parts.push(<span key={key++}>{text.slice(lastIndex)}</span>)
  }
  return parts
}

export default function App() {
  const [pdfId, setPdfId] = useState(null)
  const [pdfUrl, setPdfUrl] = useState(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [asking, setAsking] = useState(false)
  const [page, setPage] = useState(1)
  const iframeRef = useRef(null)

  const iframeSrc = useMemo(() => {
    if (!pdfUrl) return null
    return `${pdfUrl}#page=${page}&toolbar=0`
  }, [pdfUrl, page])

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
      setPdfId(data.pdf_id)
      setPdfUrl(data.url)
      setPage(1)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  async function handleAsk() {
    if (!pdfId) {
      setError('Upload a PDF first.')
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
        body: JSON.stringify({ pdf_id: pdfId, question }),
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

  function jumpToPage(p) {
    setPage(p)
  }

  return (
    <div className="app">
      <header>
        <h1>AI Citation Reference</h1>
        <p>Upload a PDF and ask questions. Click citations to jump to pages.</p>
      </header>

      <div className="grid">
        <section className="panel">
          <label className="file-input">
            <input type="file" accept="application/pdf" onChange={handleUpload} disabled={uploading} />
            <span>{uploading ? 'Uploading…' : pdfId ? 'Replace PDF' : 'Upload PDF'}</span>
          </label>

          <textarea
            placeholder="Ask a question about the PDF…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={4}
          />

          <button onClick={handleAsk} disabled={asking || !pdfId}>
            {asking ? 'Thinking…' : 'Get Answer'}
          </button>

          {error && <div className="error">{error}</div>}

          {answer && (
            <div className="answer">
              {renderAnswer(answer, jumpToPage)}
            </div>
          )}
        </section>

        <section className="panel viewer">
          {iframeSrc ? (
            <iframe ref={iframeRef} key={iframeSrc} src={iframeSrc} title="PDF viewer" />
          ) : (
            <div className="placeholder">PDF preview will appear here.</div>
          )}
        </section>
      </div>
    </div>
  )
}
