import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During local development the Vite dev server (port 3000) proxies API calls
// to the FastAPI backend (port 8000). In production the built static files are
// served directly by FastAPI, so the same relative "/api" paths work.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
  build: {
    outDir: "dist",
  },
});
