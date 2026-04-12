import { useState } from 'react'
import { queryDocuments, getDocument } from '../api/queryApi'
import DocumentViewer from '../components/DocumentViewer'
import ReportList from '../components/ReportList'
import './HomePage.css'

function HomePage() {
  const [query, setQuery] = useState('')
  const [searchLoading, setSearchLoading] = useState(false)
  const [searchError, setSearchError] = useState(null)
  const [results, setResults] = useState([])
  const [backendMessage, setBackendMessage] = useState(null)
  const [responseType, setResponseType] = useState(null)

  const [selectedPath, setSelectedPath] = useState(null)
  const [viewerLoading, setViewerLoading] = useState(false)
  const [viewerError, setViewerError] = useState(null)
  const [viewerFilename, setViewerFilename] = useState(null)
  const [viewerContent, setViewerContent] = useState(null)
  const [viewerFormat, setViewerFormat] = useState('text')

  async function handleSearch(e) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return

    setSearchLoading(true)
    setSearchError(null)
    setBackendMessage(null)
    setResults([])
    setResponseType(null)
    setSelectedPath(null)
    setViewerError(null)
    setViewerFilename(null)
    setViewerContent(null)
    setViewerFormat('text')

    try {
      const data = await queryDocuments(q)
      setResponseType(data.type ?? null)

      if (data.type === 'synthesis') {
        setViewerFilename('Synthesized answer')
        setViewerContent(data.content ?? '')
        setViewerFormat('markdown')
        setResults([])
        return
      }

      if (data.error) {
        setBackendMessage(data.error)
      }

      const rows = Array.isArray(data.results) ? data.results : []
      setResults(rows)

      if (rows.length === 1) {
        await openDocument(rows[0])
      }
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : 'Search failed — please try again.')
    } finally {
      setSearchLoading(false)
    }
  }

  async function openDocument(row) {
    const path = row.file_path ?? `/docs/${row.filename}`
    setSelectedPath(path)
    setViewerLoading(true)
    setViewerError(null)
    setViewerFormat('text')
    setViewerFilename(row.filename ?? path.split('/').pop())

    try {
      const doc = await getDocument(path)
      setViewerContent(doc.content ?? '')
      setViewerFilename(doc.filename ?? row.filename)
    } catch (err) {
      setViewerError(err instanceof Error ? err.message : 'Could not load document.')
      setViewerContent(null)
    } finally {
      setViewerLoading(false)
    }
  }

  return (
    <main className="home-main">
      <div className="home-content container">
        <form className="search-form" onSubmit={handleSearch} role="search">
          <div className="search-wrapper">
            <svg
              className="search-icon"
              viewBox="0 0 24 24"
              fill="none"
              aria-hidden="true"
            >
              <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
              <path
                d="M16.5 16.5L21 21"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
            </svg>
            <input
              type="search"
              className="search-input"
              placeholder="Ask SH-BAM about a report…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search query"
              autoComplete="off"
              spellCheck="false"
            />
            {query ? (
              <button
                type="button"
                className="search-clear"
                onClick={() => setQuery('')}
                aria-label="Clear search"
              >
                <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
                  <path
                    d="M18 6L6 18M6 6l12 12"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            ) : null}
            <button
              type="submit"
              className="search-btn"
              aria-label="Submit search"
              disabled={searchLoading}
            >
              {searchLoading ? 'Searching…' : 'Search'}
            </button>
          </div>
        </form>

        <div className="home-results" aria-live="polite">
          {searchError ? <p className="home-alert home-alert--error">{searchError}</p> : null}
          {backendMessage ? <p className="home-alert home-alert--info">{backendMessage}</p> : null}

          {!searchLoading &&
          responseType === 'retrieval' &&
          results.length === 0 &&
          !searchError &&
          !backendMessage ? (
            <p className="home-muted">No matching documents. Add PDFs to the backend docs folder and run ingest.</p>
          ) : null}

          <div className="home-panels">
            <div className="home-panel home-panel--list">
              <ReportList
                results={results}
                selectedPath={selectedPath}
                onSelect={(row) => openDocument(row)}
                disabled={viewerLoading}
              />
            </div>
            <div className="home-panel home-panel--viewer">
              {viewerError ? (
                <p className="home-alert home-alert--error">{viewerError}</p>
              ) : null}
              <DocumentViewer
                filename={viewerFilename}
                content={viewerContent}
                loading={viewerLoading}
                format={viewerFormat}
                emptyMessage={
                  responseType === 'retrieval' && results.length > 0
                    ? 'Choose a file from the list to preview its text.'
                    : 'Run a search, then select a result to preview.'
                }
              />
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}

export default HomePage
