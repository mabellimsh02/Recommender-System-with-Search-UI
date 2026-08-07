// In dev, Vite proxies "/api" to the local backend (see vite.config.js).
// In production, set VITE_API_BASE_URL to the deployed backend's URL.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

export async function searchTitles(query) {
  const res = await fetch(`${BASE_URL}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

export async function getRecommendations(title) {
  const res = await fetch(`${BASE_URL}/recommend?title=${encodeURIComponent(title)}`);
  if (!res.ok) throw new Error(`Recommend failed: ${res.status}`);
  return res.json();
}
