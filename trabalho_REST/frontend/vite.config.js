import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// O gateway Flask (gateway.py) sobe em localhost:9999.
// Em desenvolvimento o Vite faz proxy de /api e /sse para ele,
// evitando problemas de CORS. Para apontar para outro host em
// produção, defina VITE_API_URL no .env (ver api.js).
const GATEWAY = "http://localhost:9999";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: GATEWAY, changeOrigin: true },
      "/sse": { target: GATEWAY, changeOrigin: true },
    },
  },
});
