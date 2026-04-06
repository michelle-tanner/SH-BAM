/**
 * queryApi.js
 * -----------
 * All fetch() calls for the Query System (System 1).
 * Set VITE_API_URL in a .env file to override the default for production.
 *
 *   VITE_API_URL=https://your-backend.example.com
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function listDocuments() {}

export async function queryDocuments(query, dateRange) {
    const res = await fetch(`${BASE_URL}/query-system/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  if (!res.ok) {
    throw new Error(`Subscription failed: ${res.status}`)
  }

  console.log('Received response:', await res.clone().json()) // Log the response for debugging
  return res.json()
}

export async function getDocument(path) {}
