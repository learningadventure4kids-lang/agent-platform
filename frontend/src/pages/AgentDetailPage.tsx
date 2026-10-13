import { useEffect, useState, type ReactNode } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { ArrowLeft, BookOpen, Copy, KeyRound, Trash2 } from "lucide-react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import * as api from "../api/client";
import type { Agent, AgentTool } from "../types";
import { Button } from "../components/ui/Button";
import { StatusBadge } from "../components/ui/StatusBadge";

const EMPTY: Partial<Agent> = {
  agent_key: "",
  name: "",
  brand_name: "",
  system_prompt: "",
  welcome_message: "",
  suggestions: [],
  lead_fields: [],
  model: "qwen3:8b",
  temperature: 0.4,
  max_tokens: null,
  enabled: true,
  allowed_domains: [],
  provider_id: null,
  fallback_provider_id: null,
};

export function AgentDetailPage() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const { adminKey, principalKind } = useAdminAuth();
  const isCustomer = principalKind === "customer";

  const [agent, setAgent] = useState<Partial<Agent>>(EMPTY);
  const [tools, setTools] = useState<AgentTool[]>([]);
  const [providers, setProviders] = useState<api.AIProvider[]>([]);
  const [suggestionsText, setSuggestionsText] = useState("");
  const [domainsText, setDomainsText] = useState("");
  const [newToken, setNewToken] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const agentId = Number(id);

  useEffect(() => {
    if (!adminKey || isNew) return;
    api.getAgent(adminKey, agentId).then((a) => {
      setAgent(a);
      setSuggestionsText(a.suggestions.join(", "));
      setDomainsText(a.allowed_domains.join(", "));
    });
    api.getAgentTools(adminKey, agentId).then(setTools);
  }, [adminKey, agentId, isNew]);

  useEffect(() => {
    if (!adminKey || !isNew) return;
    api.listTools(adminKey).then((all) => setTools(all.map((t) => ({ ...t, granted: t.tool_key === "create_lead" }))));
  }, [adminKey, isNew]);

  useEffect(() => {
    // AI Providers hold the platform's real provider API keys and are
    // platform-operator-only (app/api/admin_providers.py never accepts a
    // customer session) -- calling this as a customer would just 401, and
    // a customer's agent can't be pointed at a specific provider_id
    // anyway (the backend silently drops that field for them), so there's
    // nothing useful to show here.
    if (adminKey && !isCustomer) api.listProviders(adminKey).then(setProviders);
  }, [adminKey, isCustomer]);

  if (!adminKey) return null;

  const enabledProviders = providers.filter((p) => p.enabled);

  const toggleTool = (tool_key: string) => {
    setTools((prev) => prev.map((t) => (t.tool_key === tool_key ? { ...t, granted: !t.granted } : t)));
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    const grantedKeys = tools.filter((t) => t.granted).map((t) => t.tool_key);
    const suggestions = suggestionsText.split(",").map((s) => s.trim()).filter(Boolean);
    const allowed_domains = domainsText.split(",").map((s) => s.trim()).filter(Boolean);

    try {
      if (isNew) {
        const created = await api.createAgent(adminKey, {
          ...agent,
          suggestions,
          allowed_domains,
          lead_fields: agent.lead_fields || [],
          tool_keys: grantedKeys,
        });
        setNewToken(created.public_token);
        navigate(`/agents/${created.id}`, { replace: true });
      } else {
        await api.updateAgent(adminKey, agentId, { ...agent, suggestions, allowed_domains } as Partial<Agent>);
        await api.updateAgentTools(adminKey, agentId, grantedKeys);
      }
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Could not save this agent.");
    } finally {
      setSaving(false);
    }
  };

  const rotate = async () => {
    const result = await api.rotateToken(adminKey, agentId);
    setNewToken(result.public_token);
  };

  const toggleEnabled = async () => {
    const updated = await api.setAgentEnabled(adminKey, agentId, !agent.enabled);
    setAgent(updated);
  };

  const remove = async () => {
    if (!confirm("Delete this agent? This cannot be undone.")) return;
    await api.deleteAgent(adminKey, agentId);
    navigate("/agents");
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <Link to="/agents" className="mb-6 inline-flex items-center gap-1.5 text-sm text-dust hover:text-parchment">
        <ArrowLeft size={14} /> Back to agents
      </Link>

      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl text-parchment">{isNew ? "New agent" : agent.brand_name}</h1>
        {!isNew && <StatusBadge status={agent.enabled ? "enabled" : "disabled"} />}
      </div>

      {newToken && (
        <div className="mb-6 rounded-xl border border-brass/30 bg-brass/10 p-4">
          <p className="mb-2 text-sm text-parchment">
            Public token (shown once -- copy it now, it can't be retrieved again):
          </p>
          <div className="flex items-center gap-2 rounded-lg border border-ink-border bg-ink px-3 py-2">
            <code className="flex-1 truncate text-sm text-brass-light">{newToken}</code>
            <button onClick={() => navigator.clipboard.writeText(newToken)} className="text-dust hover:text-parchment">
              <Copy size={14} />
            </button>
          </div>
        </div>
      )}

      <div className="space-y-4 rounded-xl border border-ink-border bg-ink-soft p-5">
        {isCustomer && isNew ? (
          <p className="text-xs text-dust">
            A unique agent ID is generated automatically from your business name once you save.
          </p>
        ) : (
          <Field label="Agent key (unique, e.g. 'kaur-jewellery')">
            <input
              value={agent.agent_key || ""}
              disabled={!isNew || isCustomer}
              onChange={(e) => setAgent({ ...agent, agent_key: e.target.value })}
              className="input"
            />
          </Field>
        )}
        <div className="grid grid-cols-2 gap-4">
          <Field label="Assistant name">
            <input value={agent.name || ""} onChange={(e) => setAgent({ ...agent, name: e.target.value })} className="input" />
          </Field>
          <Field label="Brand name">
            <input
              value={agent.brand_name || ""}
              onChange={(e) => setAgent({ ...agent, brand_name: e.target.value })}
              className="input"
            />
          </Field>
        </div>
        <Field label="System prompt (personality, objectives, rules)">
          <textarea
            value={agent.system_prompt || ""}
            onChange={(e) => setAgent({ ...agent, system_prompt: e.target.value })}
            rows={5}
            className="input resize-none"
          />
        </Field>
        <Field label="Welcome message">
          <textarea
            value={agent.welcome_message || ""}
            onChange={(e) => setAgent({ ...agent, welcome_message: e.target.value })}
            rows={2}
            className="input resize-none"
          />
        </Field>
        <Field label="Suggested prompts (comma-separated)">
          <input value={suggestionsText} onChange={(e) => setSuggestionsText(e.target.value)} className="input" />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Model">
            <input value={agent.model || ""} onChange={(e) => setAgent({ ...agent, model: e.target.value })} className="input" />
          </Field>
          <Field label="Temperature">
            <input
              type="number"
              step="0.1"
              min="0"
              max="1"
              value={agent.temperature ?? 0.4}
              onChange={(e) => setAgent({ ...agent, temperature: Number(e.target.value) })}
              className="input"
            />
          </Field>
        </div>
        <Field label="Allowed domains (comma-separated, blank = no restriction)">
          <input
            value={domainsText}
            onChange={(e) => setDomainsText(e.target.value)}
            placeholder="kaurjewellery.com, www.kaurjewellery.com"
            className="input"
          />
        </Field>
      </div>

      <div className="mt-6 rounded-xl border border-ink-border bg-ink-soft p-5">
        <p className="mb-3 text-xs uppercase tracking-wide text-dust/70">AI Provider</p>
        {isCustomer ? (
          <p className="text-sm text-dust">
            Your agent runs on the platform's default AI model. Model/temperature above let you tune its
            behavior; picking a specific provider is managed by the platform operator.
          </p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Provider">
                <select
                  value={agent.provider_id ?? ""}
                  onChange={(e) => setAgent({ ...agent, provider_id: e.target.value ? Number(e.target.value) : null })}
                  className="input"
                >
                  <option value="">Platform default</option>
                  {enabledProviders.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.display_name} ({p.model_name})
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Fallback Provider (optional)">
                <select
                  value={agent.fallback_provider_id ?? ""}
                  onChange={(e) =>
                    setAgent({ ...agent, fallback_provider_id: e.target.value ? Number(e.target.value) : null })
                  }
                  className="input"
                >
                  <option value="">None</option>
                  {enabledProviders
                    .filter((p) => p.id !== agent.provider_id)
                    .map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name}
                      </option>
                    ))}
                </select>
              </Field>
            </div>
            <p className="mt-2 text-xs text-dust">
              Model/temperature above override the provider's defaults for this agent. Only enabled providers are
              selectable -- manage them under{" "}
              <Link to="/providers" className="text-brass-light hover:underline">
                AI Providers
              </Link>
              .
            </p>
          </>
        )}
        <div className="mt-3">
          <Field label="Max Tokens (optional)">
            <input
              value={agent.max_tokens ?? ""}
              onChange={(e) => setAgent({ ...agent, max_tokens: e.target.value ? Number(e.target.value) : null })}
              className="input"
              placeholder="Provider default"
            />
          </Field>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-ink-border bg-ink-soft p-5">
        <p className="mb-3 text-xs uppercase tracking-wide text-dust/70">Tools</p>
        <div className="grid grid-cols-2 gap-2">
          {tools.map((t) => (
            <label key={t.tool_key} className="flex items-center gap-2 text-sm text-parchment/90">
              <input type="checkbox" checked={t.granted} onChange={() => toggleTool(t.tool_key)} />
              {t.name}
              {t.requires_confirmation && <span className="text-xs text-dust">(confirmation required)</span>}
            </label>
          ))}
        </div>
      </div>

      {!isNew && <ToolActivity adminKey={adminKey} agentId={agentId} />}

      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <Button onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </Button>
        {!isNew && (
          <>
            <Link to={`/agents/${agentId}/knowledge`}>
              <Button variant="secondary" className="gap-1.5">
                <BookOpen size={14} /> Knowledge base
              </Button>
            </Link>
            <Button variant="secondary" onClick={rotate} className="gap-1.5">
              <KeyRound size={14} /> Rotate token
            </Button>
            <Button variant="secondary" onClick={toggleEnabled}>
              {agent.enabled ? "Disable" : "Enable"}
            </Button>
            <Button variant="danger" onClick={remove} className="gap-1.5">
              <Trash2 size={14} /> Delete
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-xs text-dust">{label}</label>
      {children}
    </div>
  );
}

/** Read-only view onto the LangGraph orchestration layer's audit log
 * (app/services/tool_audit_service.py) -- every tool call this agent's
 * graph has attempted, including ones it correctly denied (e.g. a
 * confirmation-required tool called without confirmation). Arguments and
 * results shown here are already sanitized server-side before storage;
 * this page never has access to the raw values. */
function ToolActivity({ adminKey, agentId }: { adminKey: string; agentId: number }) {
  const [logs, setLogs] = useState<import("../types").ToolExecutionLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getAgentToolExecutions(adminKey, agentId, 50)
      .then(setLogs)
      .finally(() => setLoading(false));
  }, [adminKey, agentId]);

  return (
    <div className="mt-6 rounded-xl border border-ink-border bg-ink-soft p-5">
      <p className="mb-1 text-xs uppercase tracking-wide text-dust/70">Tool Activity</p>
      <p className="mb-3 text-xs text-dust">
        Recent tool calls the orchestration graph has made for this agent -- successes, denials
        (e.g. missing confirmation), errors, and timeouts. Arguments/results are sanitized.
      </p>
      {loading ? (
        <p className="text-sm text-dust">Loading...</p>
      ) : logs.length === 0 ? (
        <p className="text-sm text-dust">No tool calls recorded yet.</p>
      ) : (
        <div className="space-y-1.5">
          {logs.map((l) => (
            <div
              key={l.id}
              className="flex flex-wrap items-center gap-2 rounded-lg border border-ink-border bg-ink px-3 py-2 text-xs"
            >
              <StatusBadge status={l.status} />
              <span className="font-medium text-parchment">{l.tool_name}</span>
              {l.error_category && <span className="text-dust">({l.error_category.replace(/_/g, " ")})</span>}
              <span className="ml-auto text-dust">
                {l.duration_ms != null ? `${Math.round(l.duration_ms)}ms` : ""}
              </span>
              <span className="w-full text-dust/80">{new Date(l.started_at).toLocaleString()}</span>
              {l.sanitized_result && <span className="w-full text-dust-light">{l.sanitized_result}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
