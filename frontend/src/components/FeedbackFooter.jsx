import { useState } from 'react'
import { submitFeedback, subscribe } from '../api'
import './FeedbackFooter.css'

function FeedbackFooter() {
  const [selectedRating, setSelectedRating] = useState(null)
  const [comment, setComment] = useState('')
  const [commentSubmitting, setCommentSubmitting] = useState(false)
  const [commentSubmitted, setCommentSubmitted] = useState(false)
  const [commentError, setCommentError] = useState(null)

  const [email, setEmail] = useState('')
  const [emailSubmitting, setEmailSubmitting] = useState(false)
  const [emailSubmitted, setEmailSubmitted] = useState(false)
  const [emailError, setEmailError] = useState(null)

  const showCommentField = selectedRating !== null && selectedRating <= 3 && !commentSubmitted

  function handleRatingClick(rating) {
    setSelectedRating(rating)
    setCommentSubmitted(false)
    setCommentError(null)
  }

  async function handleFeedbackSubmit(e) {
    e.preventDefault()
    setCommentSubmitting(true)
    setCommentError(null)
    try {
      await submitFeedback(selectedRating, comment)
      setCommentSubmitted(true)
      setComment('')
    } catch {
      setCommentError('Could not send feedback — please try again.')
    } finally {
      setCommentSubmitting(false)
    }
  }

  async function handleEmailSubmit(e) {
    e.preventDefault()
    setEmailSubmitting(true)
    setEmailError(null)
    try {
      await subscribe(email)
      setEmailSubmitted(true)
      setEmail('')
    } catch {
      setEmailError('Could not subscribe — please try again.')
    } finally {
      setEmailSubmitting(false)
    }
  }

  return (
    <footer className="feedback-footer">
      <div className="feedback-inner container">

        <section className="feedback-section" aria-label="Helpfulness rating">
          <p className="feedback-heading">Was this helpful?</p>

          <div className="rating-row">
            <span className="rating-label">No</span>
            <div className="rating-buttons" role="group" aria-label="Rating from 1 to 5">
              {[1, 2, 3, 4, 5].map((n) => (
                <button
                  key={n}
                  className={`rating-btn${selectedRating === n ? ' rating-btn--selected' : ''}`}
                  onClick={() => handleRatingClick(n)}
                  aria-label={`Rating ${n} out of 5`}
                  aria-pressed={selectedRating === n}
                />
              ))}
            </div>
            <span className="rating-label">Yes</span>
          </div>

          {showCommentField && (
            <form className="comment-form" onSubmit={handleFeedbackSubmit}>
              <textarea
                className="comment-field"
                placeholder="What could be improved? (optional)"
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                rows={3}
                disabled={commentSubmitting}
              />
              {commentError && <p className="feedback-error">{commentError}</p>}
              <button
                type="submit"
                className="feedback-submit-btn"
                disabled={commentSubmitting}
              >
                {commentSubmitting ? 'Sending…' : 'Submit'}
              </button>
            </form>
          )}

          {commentSubmitted && selectedRating <= 3 && (
            <p className="feedback-thanks">Thanks for your feedback!</p>
          )}
        </section>

        <section className="email-section" aria-label="Email subscription">
          <p className="feedback-heading">Want weekly emails about these reports?</p>

          {!emailSubmitted ? (
            <form className="email-form" onSubmit={handleEmailSubmit}>
              <input
                type="email"
                className="email-field"
                placeholder="your@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                aria-label="Email address"
                disabled={emailSubmitting}
              />
              {emailError && <p className="feedback-error">{emailError}</p>}
              <button
                type="submit"
                className="feedback-submit-btn"
                disabled={emailSubmitting}
              >
                {emailSubmitting ? 'Subscribing…' : 'Subscribe'}
              </button>
            </form>
          ) : (
            <p className="feedback-thanks">You&apos;re subscribed!</p>
          )}
        </section>

      </div>
    </footer>
  )
}

export default FeedbackFooter
