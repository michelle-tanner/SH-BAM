import { useState } from "react";
import Footer from "./components/Footer";
import "./App.css";

function App() {
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="app">
      <main className="app-main" id="app-main">
        <div className="form-card" id="form-card">
          {/* Logo / header area */}
          <div className="form-header">
            <div className="form-icon">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <h1 className="form-title">Share Your Feedback</h1>
            <p className="form-subtitle">
              Help us improve by rating your experience and telling us what could be better.
            </p>
          </div>

          {/* Feedback form */}
          <Footer onSubmitDone={() => setSubmitted(true)} />
        </div>

        {/* Subtle footer text */}
        <p className="page-footer-text">
          Your responses are anonymous and help us improve.
        </p>
      </main>
    </div>
  );
}

export default App;
