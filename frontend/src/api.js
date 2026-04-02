/**
 * api.js
 * ------
 * All fetch() calls to the FastAPI backend live here.
 * Set VITE_API_URL in a .env file to override the default for production.
 *
 *   VITE_API_URL=https://your-backend.example.com
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * POST /feedback
 * Sends a helpfulness rating (1–5) and an optional comment.
 *
 * @param {number} rating   - Integer 1–5
 * @param {string|null} comment - Free-text comment (required by UI when rating ≤ 3)
 */
export async function submitFeedback(rating, comment = null) {
  const res = await fetch(`${BASE_URL}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ rating, comment: comment || null }),
  })
  if (!res.ok) {
    throw new Error(`Feedback submission failed: ${res.status}`)
  }
  return res.json()
}

/**
 * POST /subscribe
 * Subscribes an email address to the weekly digest.
 *
 * @param {string} email
 */
export async function subscribe(email) {
  const res = await fetch(`${BASE_URL}/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email }),
  })
  if (!res.ok) {
    throw new Error(`Subscription failed: ${res.status}`)
  }
  return res.json()
}
