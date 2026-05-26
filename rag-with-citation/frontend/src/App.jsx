import { useState } from 'react'
import { PdfViewer } from './components/PdfViewer'
import { UploadAndAsk } from './components/UploadAndAsk'
import { askQuestion, uploadDocument } from './lib/api'

export default function App() {
  const [doc, setDoc] = useState(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [asking, setAsking] = useState(false)
  const [page, setPage] = useState(1)
  const [numPages, setNumPages] = useState(0)
  const [highlightPara, setHighlightPara] = useState(null)

  async function handleUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setError('')
    setAnswer('')
    setUploading(true)
    try {
      const newDoc = await uploadDocument(file)
      setDoc(newDoc)
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
      const data = await askQuestion(doc.id, question)
      setAnswer(data.answer)
    } catch (err) {
      setError(err.message)
    } finally {
      setAsking(false)
    }
  }

  function handleCitationClick(n) {
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
        <UploadAndAsk
          doc={doc}
          question={question}
          setQuestion={setQuestion}
          answer={answer}
          error={error}
          uploading={uploading}
          asking={asking}
          onUpload={handleUpload}
          onAsk={handleAsk}
          onCitationClick={handleCitationClick}
        />
        <PdfViewer
          doc={doc}
          page={page}
          setPage={setPage}
          numPages={numPages}
          setNumPages={setNumPages}
          highlightPara={highlightPara}
          onError={setError}
        />
      </div>
    </div>
  )
}
