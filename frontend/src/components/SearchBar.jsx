import { useEffect, useRef, useState } from "react";
import { searchTitles } from "../api.js";

export default function SearchBar({ onSelect }) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef(null);

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
        setSuggestions([]);
      }
    }, 250);
    return () => clearTimeout(debounceRef.current);
  }, [query]);

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
