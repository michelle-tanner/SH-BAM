/**
 * queryApi.js
 * -----------
 * Fetch helpers for the query system (search, list, document preview).
 * Override with VITE_API_URL in `.env` for production.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * GET /query-system/list — filenames and metadata for files in the docs folder.
 */
export async function listDocuments() {
  const res = await fetch(`${BASE_URL}/query-system/list`)
  if (!res.ok) {
    throw new Error(`Could not list documents (${res.status})`)
  }
  return res.json()
}

/**
 * POST /query-system/query — semantic search over the ingested index.
 *
 * @param {string} query
 * @param {{ from: string, to: string } | null | undefined} dateRange optional ISO dates
 */
export async function queryDocuments(query, dateRange) {
  const body = { query }
  if (dateRange?.from && dateRange?.to) {
    body.date_range = { from: dateRange.from, to: dateRange.to }
  }
  const res = await fetch(`${BASE_URL}/query-system/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    throw new Error(`Search failed (${res.status})`)
  }
  return res.json()
}

/**
 * GET /query-system/document?path=... — plain text extracted from one file.
 * @param {string} filePath e.g. `/docs/report.pdf`
 */
export async function getDocument(filePath) {
  const params = new URLSearchParams({ path: filePath })
  const res = await fetch(`${BASE_URL}/query-system/document?${params}`)
  if (!res.ok) {
    throw new Error(`Could not load document (${res.status})`)
  }
  return res.json()
}
