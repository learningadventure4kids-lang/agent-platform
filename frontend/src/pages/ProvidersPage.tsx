import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { Plus, Star, Zap } from "lucide-react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import * as api from "../api/client";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Button } from "../components/ui/Button";

export function ProvidersPage() {
  const { adminKey, principalKind } = useAdminAuth();
  const [providers, setProviders] = useState<api.AIProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<number | null>(null);
  const [testResults, setTestResults] = useState<Record<number, api.ProviderTestResult>>({});

  const load = () => {
    if (!adminKey) return;
    api.listProviders(adminKey).then((p) => {
      setProviders(p);
      setLoading(false);
    });
  };

  useEffect(load, [adminKey]);

  if (!adminKey) return null;
  // AI Providers hold the platform's real LLM API keys/cost -- shared
  // infrastructure the operator configures, not a per-customer resource.
  // The backend already rejects a customer session on this route (401);
  // this redirect just keeps a customer from landing on a page that
  // would only ever show them an error.
  if (principalKind === "customer") return <Navigate to="/agents" replace />;

  const runTest = async (id: number) => {
    setTesting(id);
    try {
      const result = await api.testProvider(adminKey, id);
      setTestResults((prev) => ({ ...prev, [id]: result }));
    } finally {
      setTesting(null);
    }
  };

  const makeDefault = async (id: number) => {
    await api.setDefaultProvider(adminKey, id);
    load();
  };

  const toggleEnabled = async (p: api.AIProvider) => {
    await api.updateProvider(adminKey, p.id, { enabled: !p.enabled });
    load();
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl text-parchment">AI Providers</h1>
          <p className="text-sm text-dust">
            Configure which AI backends are available, then assign them per agent.
          </p>
        </div>
        <Link to="/providers/new">
          <Button size="sm" className="gap-1.5">
            <Plus size={14} /> Add AI Provider
          </Button>
        </Link>
      </div>

      {loading ? (
        <p className="text-sm text-dust">Loading…</p>
      ) : (
        <div className="space-y-3">
          {providers.map((p) => {
            const result = testResults[p.id];
            return (
              <div key={p.id} className="rounded-xl border border-ink-border bg-ink-soft p-5">
                <div className="mb-3 flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <Link to={`/providers/${p.id}`} className="font-medium text-parchment hover:text-brass-light">
                        {p.display_name}
                      </Link>
                      {p.is_default && (
                        <span className="inline-flex items-center gap-1 rounded-full border border-brass/30 bg-brass/10 px-2 py-0.5 text-xs text-brass-light">
                          <Star size={10} /> Default
                        </span>
                      )}
                    </div>
                    <p className="text-xs uppercase tracking-wide text-dust/70">{p.provider_type}</p>
                  </div>
                  <StatusBadge status={p.enabled ? "enabled" : "disabled"} />
                </div>

                <div className="mb-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
                  {p.base_url && (
                    <div>
                      <p className="text-xs text-dust/70">Base URL</p>
                      <p className="truncate text-dust-light">{p.base_url}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-dust/70">Model</p>
                    <p className="text-dust-light">{p.model_name}</p>
                  </div>
                  {p.api_key_configured && (
                    <div>
                      <p className="text-xs text-dust/70">API key</p>
                      <p className="text-dust-light">••••••••••••</p>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-dust/70">Agents using this</p>
                    <p className="text-dust-light">{p.agent_count}</p>
                  </div>
                </div>

                {result && (
                  <p className={`mb-3 text-xs ${result.success ? "text-emerald-300" : "text-red-300"}`}>
                    {result.success
                      ? `Connected -- ${result.latency_ms}ms`
                      : `${result.error_code}: ${result.message}`}
                  </p>
                )}

                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="secondary" disabled={testing === p.id} onClick={() => runTest(p.id)} className="gap-1.5">
                    <Zap size={13} /> {testing === p.id ? "Testing…" : "Test Connection"}
                  </Button>
                  <Link to={`/providers/${p.id}`}>
                    <Button size="sm" variant="secondary">
                      Edit
                    </Button>
                  </Link>
                  <Button size="sm" variant="secondary" onClick={() => toggleEnabled(p)}>
                    {p.enabled ? "Disable" : "Enable"}
                  </Button>
                  {!p.is_default && p.enabled && (
                    <Button size="sm" variant="ghost" onClick={() => makeDefault(p.id)}>
                      Set as default
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
          {providers.length === 0 && (
            <p className="rounded-xl border border-dashed border-ink-border px-6 py-10 text-center text-sm text-dust">
              No providers configured yet.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
