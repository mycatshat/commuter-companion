import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev-time proxy so the frontend can call same-origin "/api/..." without
// CORS trouble, regardless of what port the FastAPI backend runs on. In
// production (vite build), set VITE_API_BASE_URL instead -- see src/api.ts.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
