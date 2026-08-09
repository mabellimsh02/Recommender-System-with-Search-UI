// Displays the list of recommended movies as a grid of cards, each with a
// poster, title, genres, and a short reason it was recommended. Receives
// the list as a `recommendations` prop from App.jsx -- this component
// doesn't fetch anything itself, it just renders whatever it's given.

import { useState } from "react";

// A poster image that gracefully falls back to a "No poster" placeholder
// if there's no URL, or if the image URL fails to actually load (e.g. a
// broken/expired link) -- without this, a bad URL would show the
// browser's default broken-image icon instead of something clean.
function Poster({ src, alt }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <div className="poster-placeholder">No poster</div>;
  }
  return <img src={src} alt={alt} onError={() => setFailed(true)} />;
}

export default function ResultsGrid({ recommendations }) {
  // Nothing to show yet (e.g. before the user has searched for anything).
  if (!recommendations.length) return null;

  return (
    <div className="results-grid">
      {recommendations.map((rec) => (
        <div className="result-card" key={rec.movie_id}>
          <Poster src={rec.poster_url} alt={rec.title} />
          <h3>
            {rec.title} {rec.year ? `(${rec.year})` : ""}
          </h3>
          <p className="genres">{rec.genres.join(", ")}</p>
          <p className="reason">{rec.reason}</p>
        </div>
      ))}
    </div>
  );
}
