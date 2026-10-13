import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, Copy, KeyRound, Trash2, Upload } from "lucide-react";
import { useCustomerAuth } from "../hooks/useCustomerAuth";
import * as api from "../api/customer";
import type { AgentTool, BuilderAgent, BuilderDocument, EmbedSnippet, PlanInfo, ToolExecutionLog } from "../types";
import { AgentPreviewChat } from "../components/AgentPreviewChat";
import { Button } from "../components/ui/Button";
import { StatusBadge } from "../components/ui/StatusBadge";

export function CustomerAgentDetailPage() {
  const { id } = useParams();
  const agentId = Number(id);
  const { sessionToken } = useCustomerAuth();
  const location = useLocation() as { state?: { freshSnippet?: EmbedSnippet } };
  const navigate = useNavigate();

  const [agent, setAgent] = useState<BuilderAgent | null>(null);
  const [documents, setDocuments] = useState<BuilderDocument[]>([]);
  const [tools, setTools] = useState<AgentTool[]>([]);
  const [logs, setLogs] = useState<ToolExecutionLog[]>([]);
  const [suggestionsText, setSuggestionsText] = useState("");
  const [domainsText, setDomainsText] = useState("");
  const [snippet, setSnippet] = useState<EmbedSnippet | null>(location.state?.freshSnippet || null);
  const [copied, setCopied] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [plan, setPlan] = useState<PlanInfo | null>(null);
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = () => {
    if (!sessionToken) return;
    api.getMyAgent(sessionToken, agentId).then((a) => {
      setAgent(a);
      setSuggestionsText(a.suggestions.join(", "));
      setDomainsText(a.allowed_domains.join(", "));
    });
    api.listMyAgentDocuments(sessionToken, agentId).then(setDocuments);
    api.getMyAgentTools(sessionToken, agentId).then(setTools);
    api.getMyAgentToolExecutions(sessionToken, agentId, 50).then(setLogs);
    api.getMyPlan(sessionToken).then(setPlan);
  };

  useEffect(load, [sessionToken, agentId]);

  if (!agent) return <div className="px-6 py-10 text-sm text-dust">Loading...</div>;

  const save = async (patch: Record<string, unknown>) => {
    if (!sessionToken) return;
    setSaving(true);
    try {
      const updated = await api.updateMyAgent(sessionToken, agentId, patch);
      setAgent(updated);
      setSavedAt(Date.now());
    } finally {
      setSaving(false);
    }
  };

  const rotate = async () => {
    if (!sessionToken) return;
    const result = await api.rotateMyAgentToken(sessionToken, agentId);
    setSnippet(result);
  };

  const copySnippet = () => {
    if (!snippet) return;
    navigator.clipboard.writeText(snippet.install_snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const uploadFile = async (file: File) => {
    if (!sessionToken) return;
    setUploading(true);
    setUploadError(null);
    try {
      await api.uploadMyAgentDocument(sessionToken, agentId, file);
      api.listMyAgentDocuments(sessionToken, agentId).then(setDocuments);
    } catch (err) {
      setUploadError(err instanceof api.ApiError ? err.message : "Could not upload that file.");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  const toggleTool = async (tool_key: string) => {
    if (!sessionToken) return;
    const next = tools.map((t) => (t.tool_key === tool_key ? { ...t, granted: !t.granted } : t));
    setTools(next);
    const grantedKeys = next.filter((t) => t.granted).map((t) => t.tool_key);
    await api.updateMyAgentTools(sessionToken, agentId, grantedKeys);
  };

  const saveSuggestionsAndDomains = async () => {
    const suggestions = suggestionsText.split(",").map((s) => s.trim()).filter(Boolean);
    const allowed_domains = domainsText.split(",").map((s) => s.trim()).filter(Boolean);
    await save({ suggestions, allowed_domains });
  };

  const remove = async () => {
    if (!sessionToken) return;
    if (!confirm("Delete this agent? This cannot be undone -- its embed script will stop working immediately.")) return;
    await api.deleteMyAgent(sessionToken, agentId);
    navigate("/dashboard");
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <Link to="/dashboard" className="mb-6 inline-flex items-center gap-1.5 text-sm text-dust hover:text-parchment">
        <ArrowLeft size={14} /> My agents
      </Link>

      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl text-parchment">{agent.name}</h1>
          <p className="text-sm text-dust">{agent.brand_name}</p>
        </div>
        <StatusBadge status={agent.enabled ? "enabled" : "disabled"} />
      </div>

      {/* Live preview */}
      <div className="mb-6">
        <p className="mb-2 text-xs uppercase tracking-wide text-dust/70">
          Live preview -- try it like a visitor would
        </p>
        {sessionToken && (
          <AgentPreviewChat
            key={agent.id}
            sessionToken={sessionToken}
            agentId={agent.id}
            name={agent.name}
            brandName={agent.brand_name}
            welcomeMessage={agent.welcome_message}
            suggestions={agent.suggestions}
            accentColor={(agent.theme?.accent_color as string | undefined) || undefined}
          />
        )}
      </div>

      {/* Embed script */}
      <div className="mb-6 rounded-2xl border border-ink-border bg-ink-soft p-5">
        <p className="mb-1 text-xs uppercase tracking-wide text-dust/70">Embed script</p>
        {snippet ? (
          <>
            <p className="mb-3 text-sm text-dust">
              Paste this into your site's HTML, right before <code>&lt;/body&gt;</code>. Save it now --
              for security, the token inside it won't be shown again unless you rotate it.
            </p>
            <pre className="scrollbar-thin overflow-x-auto rounded-lg border border-ink-border bg-ink p-4 text-xs text-parchment-dim">
              {snippet.install_snippet}
            </pre>
            <div className="mt-3 flex items-center gap-2">
              <Button size="sm" variant="secondary" onClick={copySnippet} className="gap-1.5">
                {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : "Copy snippet"}
              </Button>
            </div>
          </>
        ) : (
          <>
            <p className="mb-3 text-sm text-dust">
              Your install script was only shown once, right after this agent was created (or last
              rotated). Rotate to get a new one -- the old script will stop working immediately.
            </p>
            <Button size="sm" variant="secondary" onClick={rotate} className="gap-1.5">
              <KeyRound size={14} /> Rotate & show script
            </Button>
          </>
        )}
      </div>

      {/* Settings */}
      <div className="mb-6 rounded-2xl border border-ink-border bg-ink-soft p-5">
        <p className="mb-3 text-xs uppercase tracking-wide text-dust/70">Settings</p>
        <div className="space-y-3">
          <Field label="Assistant name">
            <input
              className="input" value={agent.name}
              onChange={(e) => setAgent({ ...agent, name: e.target.value })}
              onBlur={(e) => save({ name: e.target.value })}
            />
          </Field>
          <Field label="Business name">
            <input
              className="input" value={agent.brand_name}
              onChange={(e) => setAgent({ ...agent, brand_name: e.target.value })}
              onBlur={(e) => save({ brand_name: e.target.value })}
            />
          </Field>
          <Field label="Welcome message">
            <textarea
              className="input" rows={2} value={agent.welcome_message}
              onChange={(e) => setAgent({ ...agent, welcome_message: e.target.value })}
              onBlur={(e) => save({ welcome_message: e.target.value })}
            />
          </Field>
          <Field label="System prompt">
            <textarea
              className="input font-mono text-xs" rows={5} value={agent.system_prompt}
              onChange={(e) => setAgent({ ...agent, system_prompt: e.target.value })}
              onBlur={(e) => save({ system_prompt: e.target.value })}
            />
          </Field>
          <Field label="Suggested prompts (comma-separated)">
            <input
              className="input" value={suggestionsText}
              onChange={(e) => setSuggestionsText(e.target.value)}
              onBlur={saveSuggestionsAndDomains}
            />
          </Field>
          <Field label="Allowed domains (comma-separated, blank = no restriction)">
            <input
              className="input" value={domainsText}
              onChange={(e) => setDomainsText(e.target.value)}
              onBlur={saveSuggestionsAndDomains}
              placeholder="example.com, www.example.com"
            />
          </Field>
          <div className="flex items-center justify-between">
            <span className="text-sm text-parchment/90">Enabled</span>
            <button
              onClick={() => save({ enabled: !agent.enabled })}
              className={`h-6 w-11 rounded-full transition-colors ${agent.enabled ? "bg-brass" : "bg-ink-border"}`}
            >
              <span
                className={`block h-5 w-5 rounded-full bg-ink transition-transform ${agent.enabled ? "translate-x-5" : "translate-x-0.5"}`}
              />
            </button>
          </div>
          {saving && <p className="text-xs text-dust">Saving...</p>}
          {!saving && savedAt && <p className="text-xs text-dust">Saved.</p>}
        </div>
      </div>

      {/* Knowledge base */}
      <div className="mb-6 rounded-2xl border border-ink-border bg-ink-soft p-5">
        <p className="mb-1 text-xs uppercase tracking-wide text-dust/70">Knowledge base</p>
        <p className="mb-1 text-sm text-dust">
          Upload FAQs, policies, or product docs -- your agent answers from these instead of guessing.
        </p>
        {plan && (
          <p className="mb-3 text-xs text-dust/70">
            {documents.length} of {plan.max_documents_per_agent} documents used on this agent --{" "}
            {plan.plan === "free" ? "Free" : "Plus"} plan, up to {plan.max_file_size_mb} MB each.
            {plan.plan === "free" && " Upgrade to Plus for more."}
          </p>
        )}
        <input
          ref={fileInput} type="file" className="hidden"
          accept=".pdf,.docx,.txt,.csv,.json,.md,.xlsx"
          onChange={(e) => e.target.files?.[0] && uploadFile(e.target.files[0])}
        />
        <Button
          size="sm" variant="secondary" onClick={() => fileInput.current?.click()}
          disabled={uploading || (plan != null && documents.length >= plan.max_documents_per_agent)}
          className="gap-1.5"
        >
          <Upload size={14} /> {uploading ? "Uploading..." : "Upload document"}
        </Button>
        {uploadError && <p className="mt-2 text-xs text-red-300">{uploadError}</p>}
        {documents.length > 0 && (
          <div className="mt-4 space-y-1.5">
            {documents.map((d) => (
              <div key={d.id} className="flex items-center justify-between rounded-lg border border-ink-border bg-ink px-3 py-2 text-xs">
                <span className="text-parchment">{d.original_filename}</span>
                <StatusBadge status={d.status} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tools */}
      <div className="mb-6 rounded-2xl border border-ink-border bg-ink-soft p-5">
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

      {/* Tool activity */}
      <div className="mb-6 rounded-2xl border border-ink-border bg-ink-soft p-5">
        <p className="mb-1 text-xs uppercase tracking-wide text-dust/70">Tool Activity</p>
        <p className="mb-3 text-xs text-dust">
          Recent tool calls your agent has made -- successes, denials (e.g. missing confirmation),
          errors, and timeouts. Arguments/results are sanitized.
        </p>
        {logs.length === 0 ? (
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

      <Button variant="danger" onClick={remove} className="gap-1.5">
        <Trash2 size={14} /> Delete agent
      </Button>
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
