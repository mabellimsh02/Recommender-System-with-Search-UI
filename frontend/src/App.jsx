import { useState } from "react";
import SearchBar from "./components/SearchBar.jsx";
import ResultsGrid from "./components/ResultsGrid.jsx";
import { getRecommendations } from "./api.js";

export default function App() {
  const [recommendations, setRecommendations] = useState([]);
  const [queryTitle, setQueryTitle] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSelect(title) {
    setLoading(true);
    setError(null);
    try {
      const data = await getRecommendations(title);
      setQueryTitle(data.query_title);
      setRecommendations(data.recommendations);
    } catch (err) {
      setError(err.message);
      setRecommendations([]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <h1>Movie Recommender</h1>
      <SearchBar onSelect={handleSelect} />
      {loading && <p>Loading...</p>}
      {error && <p className="error">{error}</p>}
      {queryTitle && !loading && !error && (
        <p>
          Because you liked <strong>{queryTitle}</strong>:
        </p>
      )}
      <ResultsGrid recommendations={recommendations} />
    </div>
  );
}
