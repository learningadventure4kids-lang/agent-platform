import { useEffect, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Trash2, Zap } from "lucide-react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import * as api from "../api/client";
import { Button } from "../components/ui/Button";

const REQUIRES_API_KEY = new Set(["groq", "openai", "openrouter", "azure_openai", "custom_openai", "anthropic", "google"]);
const REQUIRES_BASE_URL = new Set(["ollama", "custom_openai", "azure_openai"]);
const OPTIONAL_BASE_URL = new Set(["openrouter"]); // known default, but overridable

const LABELS: Record<string, string> = {
  ollama: "Ollama",
  groq: "Groq",
  openai: "OpenAI",
  anthropic: "Anthropic / Claude",
  google: "Google Gemini",
  openrouter: "OpenRouter",
  azure_openai: "Azure OpenAI",
  custom_openai: "Custom OpenAI-Compatible",
};

export function ProviderDetailPage() {
  const { id } = useParams();
  const isNew = id === "new";
  const navigate = useNavigate();
  const { adminKey, principalKind } = useAdminAuth();

  const [types, setTypes] = useState<{ implemented: string[]; all: string[] }>({ implemented: [], all: [] });
  const [providerType, setProviderType] = useState("ollama");
  const [displayName, setDisplayName] = useState("");
  const [baseUrl, setBaseUrl] = useState("http://localhost:11434");
  const [apiKey, setApiKey] = useState("");
  const [apiKeyConfigured, setApiKeyConfigured] = useState(false);
  const [modelName, setModelName] = useState("");
  const [temperature, setTemperature] = useState(0.4);
  const [maxTokens, setMaxTokens] = useState<string>("");
  const [enabled, setEnabled] = useState(true);
  const [isDefault, setIsDefault] = useState(false);
  const [discoveredModels, setDiscoveredModels] = useState<string[]>([]);
  const [testResult, setTestResult] = useState<api.ProviderTestResult | null>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const providerId = Number(id);

  useEffect(() => {
    if (adminKey) api.listProviderTypes(adminKey).then(setTypes);
  }, [adminKey]);

  useEffect(() => {
    if (!adminKey || isNew) return;
    api.getProvider(adminKey, providerId).then((p) => {
      setProviderType(p.provider_type);
      setDisplayName(p.display_name);
      setBaseUrl(p.base_url || "");
      setApiKeyConfigured(p.api_key_configured);
      setModelName(p.model_name);
      setTemperature(p.temperature);
      setMaxTokens(p.max_tokens ? String(p.max_tokens) : "");
      setEnabled(p.enabled);
      setIsDefault(p.is_default);
    });
  }, [adminKey, providerId, isNew]);

  if (!adminKey) return null;
  if (principalKind === "customer") return <Navigate to="/agents" replace />;

  const needsApiKey = REQUIRES_API_KEY.has(providerType);
  const needsBaseUrl = REQUIRES_BASE_URL.has(providerType) || OPTIONAL_BASE_URL.has(providerType);
  const isImplemented = types.implemented.includes(providerType);

  const save = async () => {
    setSaving(true);
    setError(null);
    const payload: Record<string, unknown> = {
      display_name: displayName,
      base_url: baseUrl || null,
      model_name: modelName,
      temperature,
      max_tokens: maxTokens ? Number(maxTokens) : null,
      enabled,
      is_default: isDefault,
    };
    if (apiKey) payload.api_key = apiKey;

    try {
      if (isNew) {
        payload.provider_type = providerType;
        const created = await api.createProvider(adminKey, payload);
        navigate(`/providers/${created.id}`, { replace: true });
      } else {
        await api.updateProvider(adminKey, providerId, payload);
        setApiKey("");
      }
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Could not save this provider.");
    } finally {
      setSaving(false);
    }
  };

  const runTest = async () => {
    setTesting(true);
    try {
      const result = await api.testProvider(adminKey, providerId);
      setTestResult(result);
    } finally {
      setTesting(false);
    }
  };

  const discover = async () => {
    const result = await api.discoverModels(adminKey, providerId);
    if (result.supported) setDiscoveredModels(result.models);
  };

  const remove = async () => {
    if (!confirm("Delete this provider? Agents using it must be reassigned first.")) return;
    try {
      await api.deleteProvider(adminKey, providerId);
      navigate("/providers");
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Could not delete this provider.");
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <Link to="/providers" className="mb-6 inline-flex items-center gap-1.5 text-sm text-dust hover:text-parchment">
        <ArrowLeft size={14} /> Back to providers
      </Link>

      <h1 className="mb-6 font-display text-2xl text-parchment">{isNew ? "Add AI Provider" : displayName}</h1>

      <div className="space-y-4 rounded-xl border border-ink-border bg-ink-soft p-5">
        <div>
          <label className="mb-1 block text-xs text-dust">Provider Type</label>
          <select
            value={providerType}
            disabled={!isNew}
            onChange={(e) => setProviderType(e.target.value)}
            className="input"
          >
            {types.all.map((t) => (
              <option key={t} value={t}>
                {LABELS[t] || t}
                {!types.implemented.includes(t) ? " (coming soon)" : ""}
              </option>
            ))}
          </select>
          {!isImplemented && (
            <p className="mt-1 text-xs text-brass-light">
              This provider type is registered but not yet implemented -- selecting it will fail until support is added.
            </p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-xs text-dust">Display Name</label>
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} className="input" placeholder="e.g. Groq (fast Llama)" />
        </div>

        {needsBaseUrl && (
          <div>
            <label className="mb-1 block text-xs text-dust">Base URL</label>
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} className="input" placeholder="https://api.groq.com/openai/v1" />
          </div>
        )}

        {needsApiKey && (
          <div>
            <label className="mb-1 block text-xs text-dust">
              API Key {apiKeyConfigured && <span className="text-emerald-300">(configured -- leave blank to keep)</span>}
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="input"
              placeholder={apiKeyConfigured ? "••••••••••••••••" : "sk-..."}
            />
          </div>
        )}

        <div>
          <label className="mb-1 block text-xs text-dust">Model</label>
          <input value={modelName} onChange={(e) => setModelName(e.target.value)} className="input" placeholder="e.g. llama-3.3-70b-versatile" />
          {!isNew && (
            <button onClick={discover} className="mt-1 text-xs text-brass-light hover:underline">
              Discover available models
            </button>
          )}
          {discoveredModels.length > 0 && (
            <select
              className="input mt-2"
              onChange={(e) => setModelName(e.target.value)}
              defaultValue=""
            >
              <option value="" disabled>
                Select a discovered model…
              </option>
              {discoveredModels.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          )}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1 block text-xs text-dust">Temperature</label>
            <input
              type="number" step="0.1" min="0" max="2"
              value={temperature}
              onChange={(e) => setTemperature(Number(e.target.value))}
              className="input"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-dust">Max Tokens (optional)</label>
            <input value={maxTokens} onChange={(e) => setMaxTokens(e.target.value)} className="input" placeholder="e.g. 1024" />
          </div>
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-parchment/90">
            <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} /> Enabled
          </label>
          <label className="flex items-center gap-2 text-sm text-parchment/90">
            <input type="checkbox" checked={isDefault} onChange={(e) => setIsDefault(e.target.checked)} /> Default provider
          </label>
        </div>
      </div>

      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}

      {testResult && (
        <p className={`mt-4 text-sm ${testResult.success ? "text-emerald-300" : "text-red-300"}`}>
          {testResult.success
            ? `Connection successful -- ${testResult.model}, ${testResult.latency_ms}ms`
            : `${testResult.error_code}: ${testResult.message}`}
        </p>
      )}

      <div className="mt-6 flex flex-wrap gap-2">
        <Button onClick={save} disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </Button>
        {!isNew && (
          <>
            <Button variant="secondary" onClick={runTest} disabled={testing} className="gap-1.5">
              <Zap size={14} /> {testing ? "Testing…" : "Test Connection"}
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
