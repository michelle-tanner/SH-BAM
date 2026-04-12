import ReactMarkdown from 'react-markdown'
import './DocumentViewer.css'

/**
 * @param {string} [filename]
 * @param {string} [content]
 * @param {boolean} [loading]
 * @param {string} [emptyMessage]
 * @param {'text' | 'markdown'} [format] — PDF/text extraction vs markdown synthesis
 */
function DocumentViewer({
  filename,
  content,
  loading,
  emptyMessage = 'Select a result to preview the full document text.',
  format = 'text',
}) {
  if (loading) {
    return (
      <div className="document-viewer document-viewer--loading" aria-live="polite">
        <p className="document-viewer-status">Loading document…</p>
      </div>
    )
  }

  if (!content) {
    return (
      <div className="document-viewer document-viewer--empty">
        <p className="document-viewer-empty">{emptyMessage}</p>
      </div>
    )
  }

  return (
    <article className="document-viewer" aria-label="Document preview">
      {filename ? <h2 className="document-viewer-title">{filename}</h2> : null}
      <div className="document-viewer-body">
        {format === 'markdown' ? (
          <ReactMarkdown>{content}</ReactMarkdown>
        ) : (
          <pre className="document-viewer-pre">{content}</pre>
        )}
      </div>
    </article>
  )
}

export default DocumentViewer
