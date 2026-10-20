import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// dev: `npm run dev` proxies /api to a locally running backend
export default defineConfig({ plugins: [react()], server: { port: 3000, proxy: { "/api": process.env.VITE_BACKEND ?? "http://localhost:8000" } } });
