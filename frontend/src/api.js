// All the code that talks to the backend lives in this one file, so
// components never call fetch() directly -- they just import these two
// functions. That keeps the URL-building and error-handling in one place.

// In dev, Vite proxies "/api" to the local backend (see vite.config.js).
// In production, set VITE_API_BASE_URL to the deployed backend's URL.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

// Calls GET /api/search?q=... -- used by SearchBar for the autocomplete
// dropdown as the user types. Returns { results: [...] }.
export async function searchTitles(query) {
  const res = await fetch(`${BASE_URL}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

// Calls GET /api/recommend?title=... -- `title` must be an exact movie
// title (App.jsx only calls this after the user picks a search suggestion,
// never with raw typed text). Returns { query_title, method, recommendations }.
export async function getRecommendations(title) {
  const res = await fetch(`${BASE_URL}/recommend?title=${encodeURIComponent(title)}`);
  if (!res.ok) throw new Error(`Recommend failed: ${res.status}`);
  return res.json();
}
