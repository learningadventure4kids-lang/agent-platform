import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Wand2 } from "lucide-react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import * as api from "../api/client";
import type { Agent } from "../types";
import { StatusBadge } from "../components/ui/StatusBadge";
import { Button } from "../components/ui/Button";

export function AgentsPage() {
  const { adminKey, principalKind } = useAdminAuth();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!adminKey) return;
    api.listAgents(adminKey).then((a) => {
      setAgents(a);
      setLoading(false);
    });
  }, [adminKey]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl text-parchment">Agents</h1>
          <p className="text-sm text-dust">
            {principalKind === "customer" ? "The agents you've created." : "One reusable platform, many businesses."}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {principalKind === "customer" && (
            <Link to="/dashboard/new">
              <Button size="sm" variant="secondary" className="gap-1.5">
                <Wand2 size={14} /> Guided setup
              </Button>
            </Link>
          )}
          <Link to="/agents/new">
            <Button size="sm" className="gap-1.5">
              <Plus size={14} /> New agent
            </Button>
          </Link>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-dust">Loading…</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-ink-border">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead>
              <tr className="border-b border-ink-border text-xs uppercase tracking-wide text-dust/70">
                <th className="px-4 py-3 font-medium">Agent</th>
                <th className="px-4 py-3 font-medium">Brand</th>
                <th className="px-4 py-3 font-medium">Model</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Tools</th>
                <th className="px-4 py-3 font-medium">Sessions</th>
                <th className="px-4 py-3 font-medium">Leads</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((a) => (
                <tr key={a.id} className="border-b border-ink-border/60 last:border-0 hover:bg-white/[0.02]">
                  <td className="px-4 py-3">
                    <Link to={`/agents/${a.id}`} className="font-medium text-parchment hover:text-brass-light">
                      {a.name}
                    </Link>
                    <p className="text-xs text-dust">{a.agent_key}</p>
                  </td>
                  <td className="px-4 py-3 text-dust-light">{a.brand_name}</td>
                  <td className="px-4 py-3 text-dust-light">{a.model}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={a.enabled ? "enabled" : "disabled"} />
                  </td>
                  <td className="px-4 py-3 tabular-nums text-dust-light">{a.tool_count}</td>
                  <td className="px-4 py-3 tabular-nums text-dust-light">{a.session_count}</td>
                  <td className="px-4 py-3 tabular-nums text-dust-light">{a.lead_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
