import { useState } from "react";

function Poster({ src, alt }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <div className="poster-placeholder">No poster</div>;
  }
  return <img src={src} alt={alt} onError={() => setFailed(true)} />;
}

export default function ResultsGrid({ recommendations }) {
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
