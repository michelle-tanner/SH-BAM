import { useState, useEffect } from 'react'
import { listDocuments } from '../api/queryApi'
import './RepositoryPage.css'

function RepositoryPage() {
  const [documents, setDocuments] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await listDocuments()
        if (!cancelled) {
          setDocuments(data.documents ?? [])
          setTotal(data.total ?? 0)
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Could not load the document list.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="repo-main">
      <div className="repo-inner container">
        <header className="repo-header">
          <h1 className="repo-title">Repository</h1>
          <p className="repo-lead">
            Files in the backend docs folder ({total} total). Index them with{' '}
            <code className="repo-code">python -m query_system.ingest</code>.
          </p>
        </header>

        {loading ? <p className="repo-status">Loading…</p> : null}
        {error ? <p className="repo-error">{error}</p> : null}

        {!loading && !error && documents.length === 0 ? (
          <p className="repo-empty">No documents found. Add PDFs, DOCX, or TXT files to backend/docs.</p>
        ) : null}

        {!loading && documents.length > 0 ? (
          <div className="repo-table-wrap">
            <table className="repo-table">
              <thead>
                <tr>
                  <th scope="col">Filename</th>
                  <th scope="col">Date</th>
                  <th scope="col">Path</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((d) => (
                  <tr key={d.file_path ?? d.filename}>
                    <td>{d.filename}</td>
                    <td>{d.doc_date || '—'}</td>
                    <td>
                      <code>{d.file_path}</code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </div>
    </main>
  )
}

export default RepositoryPage
