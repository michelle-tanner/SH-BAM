import { useState } from "react";
import FeedbackModal from "./FeedbackModal";
import "./Footer.css";

export default function Footer() {
  const [rating, setRating] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [hovered, setHovered] = useState(null);

  const handleRatingClick = (value) => {
    setRating(value);
    setShowModal(true);
  };

  const submitFeedback = async (ratingVal, comment) => {
    try {
      const res = await fetch("http://localhost:3001/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rating: ratingVal, comment }),
      });
      const data = await res.json();
      if (data.success) {
        setSubmitted(true);
        setShowModal(false);
        setTimeout(() => {
          setSubmitted(false);
          setRating(null);
        }, 3000);
      }
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    }
  };

  const handleModalSubmit = (comment) => {
    submitFeedback(rating, comment);
  };

  const handleModalClose = () => {
    setShowModal(false);
    setRating(null);
  };

  const ratingLabels = ["Awful", "Poor", "Okay", "Good", "Great"];

  return (
    <>
      <footer className="feedback-footer" id="feedback-footer">
        <div className="footer-inner">
          {submitted ? (
            <div className="thank-you" id="thank-you-message">
              <span className="thank-you-icon">✨</span>
              <span>Thank you for your feedback!</span>
            </div>
          ) : (
            <>
              <p className="footer-prompt">Was this AI response helpful?</p>
              <div className="rating-container" id="rating-container">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    key={value}
                    id={`rating-btn-${value}`}
                    className={`rating-bubble ${
                      rating === value ? "selected" : ""
                    } ${hovered !== null && hovered >= value ? "in-range" : ""}`}
                    onClick={() => handleRatingClick(value)}
                    onMouseEnter={() => setHovered(value)}
                    onMouseLeave={() => setHovered(null)}
                    aria-label={`Rate ${value} out of 5: ${ratingLabels[value - 1]}`}
                  >
                    <span className="bubble-number">{value}</span>
                    <span className="bubble-label">{ratingLabels[value - 1]}</span>
                  </button>
                ))}
              </div>
              <div className="rating-scale-labels">
                <span>Not helpful</span>
                <span>Very helpful</span>
              </div>
            </>
          )}
        </div>
      </footer>

      {showModal && (
        <FeedbackModal
          rating={rating}
          onSubmit={handleModalSubmit}
          onClose={handleModalClose}
        />
      )}
    </>
  );
}
