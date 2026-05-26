function normalizeDoc(data) {
  return {
    id: data.doc_id,
    kind: data.kind,
    url: data.url,
    paragraphs: data.paragraphs,
    pageWidth: data.page_width,
    pageHeight: data.page_height,
  }
}

async function readError(res, fallback) {
  const body = await res.json().catch(() => ({}))
  return new Error(body.detail || fallback)
}

export async function uploadDocument(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch('/api/upload', { method: 'POST', body: form })
  if (!res.ok) throw await readError(res, 'Upload failed')
  return normalizeDoc(await res.json())
}

export async function askQuestion(docId, question) {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ doc_id: docId, question }),
  })
  if (!res.ok) throw await readError(res, 'Request failed')
  return res.json()
}
