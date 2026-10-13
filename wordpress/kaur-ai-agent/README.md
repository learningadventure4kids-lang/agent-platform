# Kaur AI Agent (WordPress plugin)

Embeds an Aria Agent Platform chat widget on a WordPress site. This plugin
contains **no Python, Ollama, LangChain, or LangGraph** -- it only loads the
pre-built `assets/aria-widget.js` script (produced by the platform's
`widget/` package) and tells it which agent + backend to talk to.

## Install

1. Copy this `kaur-ai-agent/` folder into `wp-content/plugins/`.
2. In WordPress admin, go to **Plugins** and activate "Kaur AI Agent".
3. Go to **Settings -> Kaur AI Agent** and fill in:
   - **API URL** -- your Aria Agent Platform backend, e.g. `https://api.example.com`
   - **Agent Token** -- the public token for the agent you want this site to use
   - **Widget Position** -- floating bubble (site-wide) or inline (shortcode only)
4. Save.

## Usage

- **Floating mode**: once enabled, the chat bubble appears automatically in
  the bottom-right corner of every page.
- **Inline mode**: place the shortcode wherever you want the chat panel to
  appear:

  ```
  [aria_ai_agent]
  ```

## Updating the widget bundle

`assets/aria-widget.js` is a build artifact. To update it after changing the
platform's widget source:

```bash
cd widget
npm install
npm run build
cp dist/aria-widget.js ../wordpress/kaur-ai-agent/assets/aria-widget.js
```

`assets/aria-widget.css` is intentionally empty -- the widget compiles and
injects its own styles into an isolated Shadow DOM at runtime, so there is
no separate stylesheet to enqueue.

## Security notes

- The agent token stored in these settings is **public by design** (see the
  platform README's "How tokens work" section) -- it identifies which agent
  to load, not a secret credential. Even so, only paste tokens from agents
  you control.
- If a token is ever compromised or you want to revoke a previously shared
  snippet, rotate it from the Aria Agent Platform admin dashboard (Agents ->
  agent -> Rotate token) and update this settings page with the new value.
