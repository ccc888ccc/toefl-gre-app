import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, proxy /api to the FastAPI backend so there are no CORS issues and the
// frontend can use relative URLs (same as in production where one server serves both).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // expose on LAN so your phone can reach the dev server
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
