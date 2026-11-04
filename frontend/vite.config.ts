import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Forward API calls to the FastAPI backend during development.
    proxy: { "/api": process.env.VITE_API_TARGET ?? "http://127.0.0.1:8000" },
  },
});
