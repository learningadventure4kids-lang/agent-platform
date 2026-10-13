import { useEffect, useState } from "react";
import { useCustomerAuth } from "../hooks/useCustomerAuth";
import * as api from "../api/customer";
import type { BuilderAgent } from "../types";

export function BuilderAnalyticsPage() {
  const { sessionToken } = useCustomerAuth();
  const [agents, setAgents] = useState<BuilderAgent[]>([]);

  useEffect(() => {
    if (sessionToken) api.listMyAgents(sessionToken).then(setAgents);
  }, [sessionToken]);

  const totals = agents.reduce(
    (acc, a) => ({
      sessions: acc.sessions + a.session_count,
      leads: acc.leads + a.lead_count,
    }),
    { sessions: 0, leads: 0 }
  );

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="mb-1 font-display text-2xl text-parchment">Analytics</h1>
      <p className="mb-6 text-sm text-dust">A breakdown across your own agents.</p>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-ink-border bg-ink-soft px-4 py-3.5">
          <p className="font-display text-2xl text-parchment">{agents.length}</p>
          <p className="mt-0.5 text-xs text-dust">Your agents</p>
        </div>
        <div className="rounded-xl border border-ink-border bg-ink-soft px-4 py-3.5">
          <p className="font-display text-2xl text-parchment">{totals.sessions}</p>
          <p className="mt-0.5 text-xs text-dust">Total sessions</p>
        </div>
        <div className="rounded-xl border border-ink-border bg-ink-soft px-4 py-3.5">
          <p className="font-display text-2xl text-parchment">{totals.leads}</p>
          <p className="mt-0.5 text-xs text-dust">Total leads</p>
        </div>
      </div>

      <div className="overflow-x-auto rounded-xl border border-ink-border">
        <table className="w-full min-w-[500px] text-left text-sm">
          <thead>
            <tr className="border-b border-ink-border text-xs uppercase tracking-wide text-dust/70">
              <th className="px-4 py-3 font-medium">Agent</th>
              <th className="px-4 py-3 font-medium">Sessions</th>
              <th className="px-4 py-3 font-medium">Leads</th>
              <th className="px-4 py-3 font-medium">Conversion</th>
            </tr>
          </thead>
          <tbody>
            {agents.map((a) => (
              <tr key={a.id} className="border-b border-ink-border/60 last:border-0">
                <td className="px-4 py-3 text-parchment">{a.brand_name}</td>
                <td className="px-4 py-3 tabular-nums text-dust-light">{a.session_count}</td>
                <td className="px-4 py-3 tabular-nums text-dust-light">{a.lead_count}</td>
                <td className="px-4 py-3 tabular-nums text-dust-light">
                  {a.session_count ? `${Math.round((a.lead_count / a.session_count) * 100)}%` : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
