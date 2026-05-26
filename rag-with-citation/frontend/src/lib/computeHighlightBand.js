const DEFAULT_PAGE_WIDTH_PT = 612
const DEFAULT_PAGE_HEIGHT_PT = 792
const MIN_BAND_HEIGHT_PX = 8
const MIN_BAND_WIDTH_PX = 8
const BAND_PAD_PX = 2

export function computeHighlightBand({ paragraph, page, pageWidth, doc, renderedPage }) {
  if (
    !paragraph ||
    paragraph.page !== page ||
    paragraph.top == null ||
    paragraph.bottom == null
  ) {
    return null
  }
  // Prefer the actual dimensions reported by react-pdf for the rendered page;
  // fall back to the values from /api/upload, then to US Letter defaults.
  const usingRendered = renderedPage && renderedPage.pageNumber === page
  const pdfWidth = usingRendered ? renderedPage.pdfWidth : doc.pageWidth || DEFAULT_PAGE_WIDTH_PT
  const pdfHeight = usingRendered
    ? renderedPage.pdfHeight
    : doc.pageHeight || DEFAULT_PAGE_HEIGHT_PT
  const canvasWidthPx = usingRendered ? renderedPage.widthPx : pageWidth
  const canvasHeightPx = usingRendered
    ? renderedPage.heightPx
    : (pdfHeight * pageWidth) / pdfWidth
  const scale = canvasWidthPx / pdfWidth
  // Fall back to full canvas width if backend didn't report x-coords (older payloads).
  const hasX = paragraph.left != null && paragraph.right != null
  const leftPx = hasX ? Math.max(0, paragraph.left * scale - BAND_PAD_PX) : 0
  const rightPx = hasX
    ? Math.min(canvasWidthPx, paragraph.right * scale + BAND_PAD_PX)
    : canvasWidthPx
  return {
    topPx: paragraph.top * scale,
    heightPx: Math.max(MIN_BAND_HEIGHT_PX, (paragraph.bottom - paragraph.top) * scale),
    leftPx,
    widthPx: Math.max(MIN_BAND_WIDTH_PX, rightPx - leftPx),
    canvasHeightPx,
  }
}
