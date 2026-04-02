import './GuidePage.css'

const GUIDE_SECTIONS = [
  {
    title: 'What is this tool?',
    body: 'This application lets you search across curated research reports using natural-language queries. Results are ranked by relevance and recency.',
  },
  {
    title: 'How to search',
    body: 'Type a question or topic into the search bar on the home page and press Enter or click Search. The query is sent to our backend, which retrieves the most relevant report excerpts.',
  },
  {
    title: 'Feedback',
    body: 'After reviewing results, use the rating buttons in the footer to tell us how helpful the results were. Ratings of 1–3 let you leave a comment — we read every one.',
  },
  {
    title: 'Weekly digest',
    body: 'Subscribe with your email in the footer to receive a weekly roundup of newly added reports matching your interests.',
  },
]

function GuidePage() {
  return (
    <main className="guide-main">
      <div className="guide-content container">
        <header className="guide-header">
          <h1 className="guide-title">Guide</h1>
          <p className="guide-lead">
            Everything you need to know about using the Research Reports tool.
          </p>
        </header>

        <ol className="guide-list">
          {GUIDE_SECTIONS.map((section, i) => (
            <li key={i} className="guide-item">
              <span className="guide-num" aria-hidden="true">{i + 1}</span>
              <div className="guide-text">
                <h2 className="guide-section-title">{section.title}</h2>
                <p className="guide-body">{section.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </main>
  )
}

export default GuidePage
