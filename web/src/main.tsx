import React from "react";
import ReactDOM from "react-dom/client";
import { ConvexProvider, ConvexReactClient } from "convex/react";
// Self-hosted fonts (bundled by Vite — offline-ready, no CDN call).
// Space Grotesk for headings/numbers, Inter for UI text, IBM Plex Mono for logs.
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import App from "./App";
import "./index.css";
import { applyTheme, getTheme } from "./lib/theme";
applyTheme(getTheme()); // restore persisted theme before first paint

const convexUrl = import.meta.env.VITE_CONVEX_URL as string;
const convex = new ConvexReactClient(convexUrl);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConvexProvider client={convex}>
      <App />
    </ConvexProvider>
  </React.StrictMode>,
);
