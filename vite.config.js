import { defineConfig } from "vite";
import tailwindcss from '@tailwindcss/vite'
import react from "@vitejs/plugin-react";

export default defineConfig(async () => ({
  plugins: [
        react(),
        tailwindcss(),
  ],

  envPrefix: ["VITE_", "TAURI_ENV_"],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      ignored: ["**/src-tauri/**"],
    },
  },
}));