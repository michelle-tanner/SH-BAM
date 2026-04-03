import { Link, useLocation } from 'react-router-dom'
import './Header.css'

function Header() {
  const location = useLocation()

  return (
    <header className="header">
      <div className="header-inner container">
        <Link to="/" className="header-logo" aria-label="Home">
          {/* <svg className="logo-icon" viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <rect width="32" height="32" rx="6" fill="white" fillOpacity="0.15" />
            <path d="M8 22L13 10L16 17L19 13L24 22H8Z" fill="white" />
          </svg> */}
           <span className="logo-text">AbbVie Logo</span>  
        </Link>

        <nav className="header-nav" aria-label="Main navigation">
          <a
            href="https://github.com/michelle-tanner/SH-BAM"
            target="_blank"
            rel="noopener noreferrer"
            className="header-btn"
          >
            Visit the Repo
          </a>
          <Link
            to="/guide"
            className={`header-btn${location.pathname === '/guide' ? ' header-btn--active' : ''}`}
          >
            Guide
          </Link>
          <button className="header-avatar" aria-label="User account">
            <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle cx="12" cy="8" r="4" stroke="white" strokeWidth="1.5" />
              <path
                d="M4 20c0-4 3.582-7 8-7s8 3 8 7"
                stroke="white"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </nav>
      </div>
    </header>
  )
}

export default Header
