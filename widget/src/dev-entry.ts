import "./index";

// For local development only: point this at a real seeded agent token and
// a running backend to test interactively via `npm run dev`.
window.AriaWidget.mountFloating({
  agentToken: import.meta.env.VITE_DEV_AGENT_TOKEN || "pub_replace-with-a-real-seeded-token",
  apiUrl: import.meta.env.VITE_DEV_API_URL || "http://localhost:8000",
});
