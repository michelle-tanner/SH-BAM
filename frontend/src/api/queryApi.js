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

export async function queryDocuments(query, dateRange) {}

export async function getDocument(path) {}
