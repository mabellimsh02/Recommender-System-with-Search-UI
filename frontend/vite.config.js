// Configuration for Vite, the tool that runs the dev server (npm run dev)
// and builds the production bundle (npm run build) for this React app.

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()], // enables JSX + React fast-refresh during development

  server: {
    // The frontend's own code calls "/api/..." (see src/api.js). In dev,
    // the frontend and backend run on different ports (5173 vs 8000), so
    // without this the browser would try to hit /api on port 5173 and
    // get a 404. This proxy quietly forwards any /api request to the
    // local backend instead. (Not used in production -- there,
    // VITE_API_BASE_URL points directly at the deployed backend's URL.)
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
