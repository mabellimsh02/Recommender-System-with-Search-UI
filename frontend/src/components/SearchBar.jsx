// A text input with an autocomplete dropdown. As the user types, this
// queries the backend's search endpoint and shows matching movie titles;
// clicking one calls the `onSelect` prop (passed down from App.jsx) with
// that movie's exact title, which App then uses to fetch recommendations.

import { useEffect, useRef, useState } from "react";
import { searchTitles } from "../api.js";

export default function SearchBar({ onSelect }) {
  const [query, setQuery] = useState("");           // current text in the input
  const [suggestions, setSuggestions] = useState([]); // matching movies from the API
  const [open, setOpen] = useState(false);            // whether the dropdown is visible
  const debounceRef = useRef(null);                   // holds the pending debounce timer

  // Re-runs every time `query` changes. We don't want to hit the API on
  // every single keystroke (that's wasteful and can make results flicker
  // out of order), so we "debounce": wait 250ms after the user stops
  // typing before actually searching. If they type again before that,
  // the previous timer is cancelled and a new one starts.
  useEffect(() => {
    if (!query.trim()) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const data = await searchTitles(query);
        setSuggestions(data.results);
        setOpen(data.results.length > 0);
      } catch {
        // A failed search just means no suggestions -- not worth showing
        // an error for something as minor as autocomplete not loading.
        setSuggestions([]);
      }
    }, 250);
    // Cleanup: if this effect re-runs (query changed again) or the
    // component unmounts before the timer fires, cancel it.
    return () => clearTimeout(debounceRef.current);
  }, [query]);

  // Called when the user clicks one of the dropdown suggestions.
  function handleSelect(movie) {
    setQuery(movie.title);
    setOpen(false);
    onSelect(movie.title);
  }

  return (
    <div className="search-bar">
      <input
        type="text"
        placeholder="Search for a movie you like..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        // A plain onBlur would close the dropdown before the click on a
        // suggestion below it gets a chance to register, so we delay it
        // slightly. The suggestions themselves use onMouseDown (fires
        // before blur) rather than onClick to select reliably.
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && (
        <ul className="suggestions">
          {suggestions.map((movie) => (
            <li key={movie.movie_id} onMouseDown={() => handleSelect(movie)}>
              {movie.title} {movie.year ? `(${movie.year})` : ""}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
