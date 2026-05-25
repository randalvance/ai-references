import { useMemo, useState } from 'react'

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

export default function App() {
  const [doc, setDoc] = useState(null) // { id, kind, url?, paragraphs? }
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [asking, setAsking] = useState(false)
  const [page, setPage] = useState(1)
  const [highlightPara, setHighlightPara] = useState(null)

  const iframeSrc = useMemo(() => {
    if (!doc || doc.kind !== 'pdf') return null
    return `${doc.url}#page=${page}&toolbar=0`
  }, [doc, page])

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
      setPage(n)
    } else {
      setHighlightPara(n)
      const el = document.getElementById(`para-${n}`)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
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

        <section className="panel viewer">
          {!doc && <div className="placeholder">Document preview will appear here.</div>}

          {doc?.kind === 'pdf' && iframeSrc && (
            <iframe key={iframeSrc} src={iframeSrc} title="PDF viewer" />
          )}

          {doc?.kind === 'docx' && (
            <div className="docx-view">
              {doc.paragraphs?.map((p) => (
                <p
                  key={p.index}
                  id={`para-${p.index}`}
                  className={highlightPara === p.index ? 'para highlight' : 'para'}
                >
                  <span className="para-num">¶ {p.index}</span>
                  {p.text}
                </p>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
