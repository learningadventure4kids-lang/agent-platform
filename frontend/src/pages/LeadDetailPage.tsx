import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import * as api from "../api/client";
import type { ChatMessage, Lead } from "../types";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Button } from "../components/ui/Button";

export function LeadDetailPage() {
  const { id } = useParams();
  const { adminKey } = useAdminAuth();
  const [lead, setLead] = useState<Lead | null>(null);
  const [conversation, setConversation] = useState<ChatMessage[]>([]);
  const [notes, setNotes] = useState("");
  const leadId = Number(id);

  const load = () => {
    if (!adminKey) return;
    api.getLead(adminKey, leadId).then((l) => {
      setLead(l);
      setNotes((l.metadata_json.admin_notes as string) || "");
    });
    api.getLeadConversation(adminKey, leadId).then((r) => setConversation(r.messages));
  };

  useEffect(load, [adminKey, leadId]);

  if (!lead || !adminKey) return <div className="px-6 py-8 text-sm text-dust">Loading…</div>;

  const setStatus = async (status: string) => {
    await api.updateLead(adminKey, leadId, { status });
    load();
  };

  const saveNotes = async () => {
    await api.updateLead(adminKey, leadId, { notes });
    load();
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <Link to="/leads" className="mb-6 inline-flex items-center gap-1.5 text-sm text-dust hover:text-parchment">
        <ArrowLeft size={14} /> Back to leads
      </Link>

      <div className="mb-6 flex items-center justify-between">
        <h1 className="font-display text-2xl text-parchment">{lead.name || "Unnamed visitor"}</h1>
        <StatusBadge status={lead.status} />
      </div>

      <div className="mb-6 grid grid-cols-2 gap-4 rounded-xl border border-ink-border bg-ink-soft p-5 sm:grid-cols-3">
        <Info label="Contact" value={lead.email || lead.phone} />
        <Info label="Source" value={lead.source} />
        <Info label="Score" value={String(lead.score)} />
        {Object.entries(lead.metadata_json)
          .filter(([k]) => k !== "admin_notes")
          .map(([k, v]) => (
            <Info key={k} label={k.replace(/_/g, " ")} value={String(v ?? "")} />
          ))}
      </div>

      <div className="mb-6 rounded-xl border border-ink-border bg-ink-soft p-5">
        <p className="mb-3 text-xs uppercase tracking-wide text-dust/70">Actions</p>
        <div className="mb-4 flex flex-wrap gap-2">
          <Button size="sm" variant="secondary" onClick={() => setStatus("contacted")}>
            Mark contacted
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setStatus("converted")}>
            Mark converted
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setStatus("closed")}>
            Close lead
          </Button>
        </div>
        <label className="mb-1 block text-xs text-dust">Notes</label>
        <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} className="input mb-3 resize-none" />
        <Button size="sm" onClick={saveNotes}>
          Save notes
        </Button>
      </div>

      <div className="rounded-xl border border-ink-border bg-ink-soft p-5">
        <p className="mb-3 text-xs uppercase tracking-wide text-dust/70">Conversation</p>
        <div className="scrollbar-thin max-h-96 space-y-3 overflow-y-auto">
          {conversation.map((m, i) => (
            <p key={i} className="text-sm">
              <span className={m.role === "user" ? "font-medium text-brass-light" : "font-medium text-dust-light"}>
                {m.role === "user" ? "Visitor: " : "Assistant: "}
              </span>
              <span className="text-parchment/90">{m.content}</span>
            </p>
          ))}
          {conversation.length === 0 && <p className="text-sm text-dust">No conversation recorded.</p>}
        </div>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-xs capitalize uppercase tracking-wide text-dust/70">{label}</p>
      <p className="mt-0.5 text-sm text-parchment">{value || "—"}</p>
    </div>
  );
}
