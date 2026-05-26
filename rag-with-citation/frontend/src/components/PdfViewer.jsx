import { useEffect, useMemo, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import { computeHighlightBand } from '../lib/computeHighlightBand'

const MIN_VIEWER_WIDTH_PX = 320
const VIEWER_HORIZONTAL_PAD_PX = 24
const INITIAL_PAGE_WIDTH_PX = 800

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

export function PdfViewer({
  doc,
  page,
  setPage,
  numPages,
  setNumPages,
  highlightPara,
  onError,
}) {
  const viewerRef = useRef(null)
  const [pageWidth, setPageWidth] = useState(INITIAL_PAGE_WIDTH_PX)
  const [renderedPage, setRenderedPage] = useState(null)

  useEffect(() => {
    const el = viewerRef.current
    if (!el) return
    const update = () =>
      setPageWidth(
        Math.max(MIN_VIEWER_WIDTH_PX, el.clientWidth - VIEWER_HORIZONTAL_PAD_PX),
      )
    update()
    const ro = new ResizeObserver(update)
    ro.observe(el)
    return () => ro.disconnect()
  }, [doc])

  const paragraph = useMemo(() => {
    if (!highlightPara || !doc?.paragraphs) return null
    return doc.paragraphs.find((p) => p.index === highlightPara) ?? null
  }, [highlightPara, doc])

  const highlightBand = useMemo(
    () => computeHighlightBand({ paragraph, page, pageWidth, doc, renderedPage }),
    [paragraph, page, pageWidth, doc, renderedPage],
  )

  return (
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
              onLoadError={(err) => onError(`Failed to load PDF: ${err.message}`)}
              loading={<div className="placeholder">Loading PDF…</div>}
            >
              <div className="pdf-page-stack">
                <Page
                  pageNumber={page}
                  width={pageWidth}
                  renderAnnotationLayer={false}
                  renderTextLayer={true}
                  onRenderSuccess={(p) => {
                    const vp = p.getViewport({ scale: 1 })
                    setRenderedPage({
                      pageNumber: p.pageNumber,
                      pdfWidth: vp.width,
                      pdfHeight: vp.height,
                      widthPx: pageWidth,
                      heightPx: (vp.height * pageWidth) / vp.width,
                    })
                  }}
                />
                {highlightBand && (
                  <div
                    className="para-highlight-band"
                    style={{
                      top: `${highlightBand.topPx}px`,
                      left: `${highlightBand.leftPx}px`,
                      width: `${highlightBand.widthPx}px`,
                      height: `${highlightBand.heightPx}px`,
                    }}
                  />
                )}
              </div>
            </Document>
          </div>
        </div>
      )}
    </section>
  )
}
