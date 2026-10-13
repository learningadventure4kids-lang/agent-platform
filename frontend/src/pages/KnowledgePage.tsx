import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import * as api from "../api/client";
import type { Agent } from "../types";
import { KnowledgeBase } from "../components/knowledge/KnowledgeBase";

export function KnowledgePage() {
  const { id } = useParams();
  const { adminKey } = useAdminAuth();
  const [agent, setAgent] = useState<Agent | null>(null);
  const agentId = Number(id);

  useEffect(() => {
    if (adminKey) api.getAgent(adminKey, agentId).then(setAgent);
  }, [adminKey, agentId]);

  if (!adminKey || !agent) return <div className="px-6 py-8 text-sm text-dust">Loading…</div>;

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <Link
        to={`/agents/${agentId}`}
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-dust hover:text-parchment"
      >
        <ArrowLeft size={14} /> Back to {agent.brand_name}
      </Link>

      <p className="mb-1 text-xs uppercase tracking-wide text-dust/70">Agent: {agent.name}</p>
      <KnowledgeBase adminKey={adminKey} agentId={agentId} />
    </div>
  );
}
