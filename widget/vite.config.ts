import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Library build: one self-contained script the host page drops in with a
// <script> tag. React/ReactDOM are bundled (not externalized) so the host
// site never needs React installed. CSS is imported with `?inline` in
// src/index.tsx and injected into a Shadow DOM root at runtime, so there is
// no separate stylesheet to link and the widget's styles can never leak
// into (or be overridden by) the host page's CSS.
export default defineConfig({
  plugins: [react()],
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    lib: {
      entry: "src/index.tsx",
      name: "AriaWidget",
      formats: ["iife"],
      fileName: () => "aria-widget.js",
    },
    cssCodeSplit: false,
    outDir: "dist",
    emptyOutDir: true,
  },
});
