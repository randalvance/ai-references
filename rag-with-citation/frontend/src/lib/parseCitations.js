const CITATION_REGEX = /\[\[para:(\d+)\]\]/g

export function parseCitations(text) {
  const parts = []
  let lastIndex = 0
  let match
  while ((match = CITATION_REGEX.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, match.index) })
    }
    parts.push({ type: 'citation', n: Number(match[1]) })
    lastIndex = CITATION_REGEX.lastIndex
  }
  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) })
  }
  return parts
}
