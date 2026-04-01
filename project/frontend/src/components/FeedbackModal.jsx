import { useState } from "react";
import "./FeedbackModal.css";

export default function FeedbackModal({ rating, onSubmit, onClose }) {
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    await onSubmit(comment);
    setSubmitting(false);
  };

  const handleChipClick = async (chipText) => {
    setSubmitting(true);
    await onSubmit(chipText);
    setSubmitting(false);
  };

  const negativeChips = ["Inaccurate", "Too Slow", "Too Long", "Confusing"];
  const positiveChips = ["Great Detail", "Lightning Fast", "Very Helpful", "Perfect Length"];
  const chips = rating <= 3 ? negativeChips : positiveChips;

  const ratingDescriptions = {
    1: "We're sorry it was awful. What went wrong?",
    2: "We'd like to do better. What was the issue?",
    3: "What could have made this more helpful?",
    4: "We are glad it was good! What did you like?",
    5: "Awesome! What did you love about it?",
  };

  return (
    <div className="modal-overlay" id="feedback-modal-overlay" onClick={onClose}>
      <div
        className="modal-container"
        id="feedback-modal"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="modal-header">
          <div className="modal-rating-badge" id="modal-rating-badge">
            <span className="modal-rating-value">{rating}</span>
            <span className="modal-rating-out">/5</span>
          </div>
          <button
            className="modal-close"
            id="modal-close-btn"
            onClick={onClose}
            aria-label="Close feedback modal"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M4 4l8 8M12 4l-8 8"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="modal-body">
          <h3 className="modal-title">Tell us more</h3>
          <p className="modal-description">
            {ratingDescriptions[rating] ||
              "Help us understand what we can improve."}
          </p>

          <div className="chips-container">
            {chips.map(chip => (
              <button
                type="button"
                key={chip}
                className="chip-btn"
                onClick={() => handleChipClick(chip)}
                disabled={submitting}
              >
                {chip}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="modal-form">
            <div className="textarea-wrapper">
              <textarea
                id="feedback-comment"
                className="modal-textarea"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Describe the issues you encountered..."
                rows={4}
                maxLength={500}
                autoFocus
              />
              <span className="char-count">
                {comment.length}/500
              </span>
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-ghost"
                id="modal-cancel-btn"
                onClick={onClose}
                disabled={submitting}
              >
                Cancel
              </button>
              <button
                type="submit"
                className={`btn ${comment.trim() ? "btn-primary" : "btn-secondary"}`}
                id="modal-submit-btn"
                disabled={submitting}
              >
                {submitting ? (
                  <span className="btn-loading">
                    <span className="spinner"></span>
                    Sending...
                  </span>
                ) : (
                  comment.trim() ? "Submit Feedback" : "Skip & Submit"
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
