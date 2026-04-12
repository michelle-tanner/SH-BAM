import './ReportList.css'

function ReportList({ results, selectedPath, onSelect, disabled }) {
  if (!results?.length) {
    return null
  }

  return (
    <div className="report-list" role="list" aria-label="Search results">
      <h2 className="report-list-title">Results</h2>
      <ul className="report-list-items">
        {results.map((row) => {
          const path = row.file_path ?? `/docs/${row.filename}`
          const isActive = selectedPath === path
          return (
            <li key={path} className="report-list-item" role="listitem">
              <button
                type="button"
                className={`report-list-row${isActive ? ' report-list-row--active' : ''}`}
                onClick={() => onSelect?.(row)}
                disabled={disabled}
              >
                <span className="report-list-name">{row.filename}</span>
                {row.doc_date ? (
                  <span className="report-list-meta">{row.doc_date}</span>
                ) : null}
                {row.score != null ? (
                  <span className="report-list-score">score {row.score}</span>
                ) : null}
                {row.snippet ? (
                  <span className="report-list-snippet">{row.snippet}</span>
                ) : null}
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default ReportList
