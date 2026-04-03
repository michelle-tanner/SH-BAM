import { useState } from 'react'
import { queryDocuments } from '../api/queryApi'
import DocumentViewer from '../components/DocumentViewer'
import ReportList from '../components/ReportList'
import './HomePage.css'

function HomePage() {
  const [query, setQuery] = useState('')

  function handleSearch(e) {
    e.preventDefault()
    // TODO: send query to backend
    console.log('Search query:', query)
  }

  return (
    <main className="home-main">
      <div className="home-content container">
        {/* <h1 className="home-title">Research Reports</h1>
        <p className="home-subtitle">
          Search across curated academic and industry reports.
        </p> */}

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
              placeholder="Ask SH-BAM about a report..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search query"
              autoComplete="off"
              spellCheck="false"
            />
            {query && (
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
            )}
            <button type="submit" className="search-btn" aria-label="Submit search">
              Search
            </button>
          </div>
        </form>
      </div>
    </main>
  )
}

export default HomePage
