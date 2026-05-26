import { AnswerWithCitations } from './AnswerWithCitations'

export function UploadAndAsk({
  doc,
  question,
  setQuestion,
  answer,
  error,
  uploading,
  asking,
  onUpload,
  onAsk,
  onCitationClick,
}) {
  return (
    <section className="panel">
      <label className="file-input">
        <input
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={onUpload}
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

      <button onClick={onAsk} disabled={asking || !doc}>
        {asking ? 'Thinking…' : 'Get Answer'}
      </button>

      {error && <div className="error">{error}</div>}

      <AnswerWithCitations answer={answer} onCitationClick={onCitationClick} />
    </section>
  )
}
