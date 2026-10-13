import { Navigate } from "react-router-dom";
import { useAdminAuth } from "../hooks/useAdminAuth";

export function SettingsPage() {
  const { principalKind } = useAdminAuth();
  // Platform-wide config (env vars, token-hashing secret, etc.) is
  // operator-only, same boundary as AI Providers.
  if (principalKind === "customer") return <Navigate to="/agents" replace />;

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <h1 className="mb-1 font-display text-2xl text-parchment">Settings</h1>
      <p className="mb-6 text-sm text-dust">Platform-level configuration lives in environment variables.</p>

      <div className="space-y-4 rounded-xl border border-ink-border bg-ink-soft p-5 text-sm">
        <Row label="Ollama model / base URL" value="OLLAMA_MODEL / OLLAMA_BASE_URL (backend/.env)" />
        <Row label="Database" value="DATABASE_URL -- SQLite by default, Postgres-ready" />
        <Row label="Admin login" value="ADMIN_USERNAME / ADMIN_PASSWORD (backend/.env)" />
        <Row label="Token hashing key" value="TOKEN_HASH_SECRET -- rotating this invalidates all agent tokens" />
        <Row label="Rate limits" value="RATE_LIMIT_PER_MINUTE / RATE_LIMIT_PER_MINUTE_PER_IP" />
      </div>

      <p className="mt-6 text-xs text-dust">
        Per-agent settings (prompt, branding, tools, domains, tokens) are managed from each agent's own
        page under Agents, not here.
      </p>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 border-b border-ink-border/60 pb-3 last:border-0 last:pb-0">
      <span className="text-xs uppercase tracking-wide text-dust/70">{label}</span>
      <span className="text-parchment/90">{value}</span>
    </div>
  );
}
