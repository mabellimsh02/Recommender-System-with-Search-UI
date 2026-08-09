// The real entry point of the React app -- this is the first JS file that
// runs (see the <script> tag in index.html). All it does is find the empty
// <div id="root"> in index.html and render our <App /> component into it.
// Everything else (the search bar, results grid, API calls) lives inside App.

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  // StrictMode is a development-only helper that highlights potential bugs
  // (e.g. by intentionally double-invoking some functions) -- it has no
  // effect on the production build.
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
