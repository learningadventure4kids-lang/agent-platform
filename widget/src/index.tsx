import React from "react";
import ReactDOM from "react-dom/client";
import { AriaChatWidget } from "./AriaChatWidget";
// `?inline` makes Vite return the fully compiled CSS as a string instead of
// injecting a <link>/<style> into document.head -- we inject it ourselves
// into the Shadow DOM below, so host page styles can never affect the
// widget and the widget's styles can never leak out.
// eslint-disable-next-line import/no-unresolved
import widgetCss from "./index.css?inline";

export interface MountConfig {
  agentToken: string;
  /** Base URL of the backend API. Optional -- if omitted, it's inferred
   * from the <script> tag that loaded this widget (same origin the
   * `aria-widget.js` file itself was served from), so a standard install
   * snippet never needs to hardcode it. Pass this explicitly only when
   * the widget script and the API are deliberately served from different
   * origins (e.g. a CDN-hosted widget script talking to your own API). */
  apiUrl?: string;
  /** CSS selector or element to render into. Defaults to a new full-size
   * container appended to <body> if omitted (fine for mountFloating; for
   * inline mount() you'll usually want to pass your own container). */
  target?: string | HTMLElement;
}

// Captured at module-evaluation time -- i.e. while this very script is
// running as a classic (non-module, non-async/defer) <script src="...">
// tag, which is the only moment `document.currentScript` reliably points
// at it. `mountFloating`/`mount` are always called from a *second*
// <script> block after this one has already finished loading, so this
// has to be grabbed up front and remembered, not looked up lazily inside
// those calls (by then `document.currentScript` would be null or point
// at the wrong tag).
const SELF_SCRIPT_URL =
  typeof document !== "undefined" && document.currentScript instanceof HTMLScriptElement
    ? document.currentScript.src
    : "";

function resolveApiUrl(explicit?: string): string {
  if (explicit) return explicit;
  if (SELF_SCRIPT_URL) {
    try {
      return new URL(SELF_SCRIPT_URL).origin;
    } catch {
      /* fall through to the error below */
    }
  }
  throw new Error(
    "AriaWidget: couldn't automatically determine the API URL (the widget script wasn't loaded via a " +
      "plain <script src=\"...\"> tag, e.g. it was loaded async/defer or as a module). Pass it explicitly: " +
      "AriaWidget.mountFloating({ agentToken, apiUrl: \"https://your-api.example.com\" })."
  );
}

function resolveTarget(target?: string | HTMLElement): HTMLElement {
  if (target instanceof HTMLElement) return target;
  if (typeof target === "string") {
    const el = document.querySelector(target);
    if (el instanceof HTMLElement) return el;
  }
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

function renderInShadow(host: HTMLElement, config: MountConfig, floating: boolean) {
  // Each mount gets its own shadow root, so multiple widgets (or repeated
  // mount calls) never collide.
  const shadowHost = document.createElement("div");
  host.appendChild(shadowHost);
  const shadowRoot = shadowHost.attachShadow({ mode: "open" });

  const style = document.createElement("style");
  style.textContent = widgetCss;
  shadowRoot.appendChild(style);

  const mountPoint = document.createElement("div");
  mountPoint.className = "aria-widget-root";
  if (!floating) {
    mountPoint.style.width = "100%";
    mountPoint.style.height = "100%";
  }
  shadowRoot.appendChild(mountPoint);

  const root = ReactDOM.createRoot(mountPoint);
  root.render(
    <React.StrictMode>
      <AriaChatWidget agentToken={config.agentToken} apiUrl={resolveApiUrl(config.apiUrl)} floating={floating} />
    </React.StrictMode>
  );

  return { unmount: () => root.unmount(), host: shadowHost };
}

const AriaWidget = {
  /** Renders the widget inline, filling the given container. Use this when
   * you want the chat to live in a specific spot on the page (e.g. a
   * WordPress shortcode's output div) rather than as a floating bubble. */
  mount(config: MountConfig) {
    const target = resolveTarget(config.target);
    return renderInShadow(target, config, false);
  },

  /** Renders a floating launcher button in the bottom-right corner that
   * opens a chat panel on click -- no target container needed. */
  mountFloating(config: Omit<MountConfig, "target">) {
    const container = document.createElement("div");
    document.body.appendChild(container);
    return renderInShadow(container, config, true);
  },
};

declare global {
  interface Window {
    AriaWidget: typeof AriaWidget;
  }
}

window.AriaWidget = AriaWidget;

export default AriaWidget;
