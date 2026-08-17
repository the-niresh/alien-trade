import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [
    tailwindcss(),
    react(),
    VitePWA({
      registerType: "autoUpdate",
      workbox: {
        importScripts: ["/sw-push.js"],
      },
      manifest: {
        name: "Alien-Trade",
        short_name: "Alien-Trade",
        description: "Autonomous BSC trading agent — PnL, drawdown, kill switch",
        theme_color: "#0b0f17",
        background_color: "#0b0f17",
        display: "standalone",
        start_url: "/",
        icons: [
          { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
    }),
  ],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
    // Monorepo: the Convex API is generated at the repo root (../../convex/_generated)
    // and imports "convex/server". On Vercel only web/'s deps install, so force all
    // convex/react/react-dom resolution to web/node_modules (one copy) to fix the build.
    dedupe: ["convex", "react", "react-dom"],
  },
  server: { host: true, port: 5173 },
});
