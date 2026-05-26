const DEFAULT_PAGE_WIDTH_PT = 612
const DEFAULT_PAGE_HEIGHT_PT = 792
const MIN_BAND_HEIGHT_PX = 8

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
  return {
    topPx: paragraph.top * scale,
    heightPx: Math.max(MIN_BAND_HEIGHT_PX, (paragraph.bottom - paragraph.top) * scale),
    widthPx: canvasWidthPx,
    canvasHeightPx,
  }
}
