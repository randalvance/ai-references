import { parseCitations } from '../lib/parseCitations'

export function AnswerWithCitations({ answer, onCitationClick }) {
  if (!answer) return null
  const parts = parseCitations(answer)
  return (
    <div className="answer">
      {parts.map((part, i) =>
        part.type === 'text' ? (
          <span key={i}>{part.value}</span>
        ) : (
          <a
            key={i}
            href="#"
            className="citation"
            onClick={(e) => {
              e.preventDefault()
              onCitationClick(part.n)
            }}
          >
            [¶ {part.n}]
          </a>
        ),
      )}
    </div>
  )
}
