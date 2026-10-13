import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAdminAuth } from "../hooks/useAdminAuth";
import * as api from "../api/client";
import type { Agent, Lead, LeadStats } from "../types";
import { StatusBadge } from "../components/ui/StatusBadge";

export function LeadsPage() {
  const { adminKey } = useAdminAuth();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<LeadStats | null>(null);
  const [agentFilter, setAgentFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  useEffect(() => {
    if (adminKey) api.listAgents(adminKey).then(setAgents);
  }, [adminKey]);

  useEffect(() => {
    if (!adminKey) return;
    const filters = {
      agent_id: agentFilter ? Number(agentFilter) : undefined,
      status: statusFilter || undefined,
    };
    api.listLeads(adminKey, filters).then(setLeads);
    api.getLeadStats(adminKey, filters.agent_id).then(setStats);
  }, [adminKey, agentFilter, statusFilter]);

  const agentName = (id: number) => agents.find((a) => a.id === id)?.brand_name || `Agent #${id}`;

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <h1 className="mb-1 font-display text-2xl text-parchment">Leads</h1>
      <p className="mb-6 text-sm text-dust">Visitors who confirmed a request, across every agent.</p>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        {stats &&
          (["total", "new", "qualified", "contacted", "converted"] as const).map((k) => (
            <div key={k} className="rounded-xl border border-ink-border bg-ink-soft px-4 py-3.5">
              <p className="font-display text-2xl text-parchment">{stats[k]}</p>
              <p className="mt-0.5 text-xs capitalize text-dust">{k}</p>
            </div>
          ))}
      </div>

      <div className="mb-4 flex gap-3">
        <select value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)} className="input w-auto">
          <option value="">All agents</option>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>
              {a.brand_name}
            </option>
          ))}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input w-auto">
          <option value="">All statuses</option>
          {["new", "qualified", "contacted", "converted", "closed"].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto rounded-xl border border-ink-border">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead>
            <tr className="border-b border-ink-border text-xs uppercase tracking-wide text-dust/70">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Agent</th>
              <th className="px-4 py-3 font-medium">Contact</th>
              <th className="px-4 py-3 font-medium">Score</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => (
              <tr key={l.id} className="border-b border-ink-border/60 last:border-0 hover:bg-white/[0.02]">
                <td className="px-4 py-3">
                  <Link to={`/leads/${l.id}`} className="font-medium text-parchment hover:text-brass-light">
                    {l.name || "Unnamed visitor"}
                  </Link>
                </td>
                <td className="px-4 py-3 text-dust-light">{agentName(l.agent_id)}</td>
                <td className="px-4 py-3 text-dust-light">{l.email || l.phone || "—"}</td>
                <td className="px-4 py-3 tabular-nums text-dust-light">{l.score}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={l.status} />
                </td>
                <td className="px-4 py-3 text-dust-light">{new Date(l.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {leads.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-sm text-dust">
                  No leads yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
