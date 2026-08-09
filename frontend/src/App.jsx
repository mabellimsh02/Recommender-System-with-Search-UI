// The top-level component: owns all the page's state (what movie was
// picked, the recommendations we got back, loading/error status) and
// wires the two child components together --
//   SearchBar:    lets the user find and pick a movie
//   ResultsGrid:  displays the recommendations for whatever was picked
// Data flows one way: SearchBar reports a pick up to App via onSelect,
// App fetches recommendations and passes them down to ResultsGrid as props.

import { useState } from "react";
import SearchBar from "./components/SearchBar.jsx";
import ResultsGrid from "./components/ResultsGrid.jsx";
import { getRecommendations } from "./api.js";

export default function App() {
  // recommendations: the list currently shown in the results grid
  const [recommendations, setRecommendations] = useState([]);
  // queryTitle: the movie that was searched for, shown in "Because you liked X"
  const [queryTitle, setQueryTitle] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  // Called by SearchBar once the user clicks a suggestion. `title` is an
  // exact movie title (from the dropdown, not raw typed text), which the
  // backend's /api/recommend endpoint requires.
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
