import { useEffect, useState } from "react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import * as api from "../api/client";

export function SessionsPage() {
  const { adminKey } = useAdminAuth();
  const [rows, setRows] = useState<api.SessionRow[]>([]);

  useEffect(() => {
    if (adminKey) api.listSessions(adminKey).then(setRows);
  }, [adminKey]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-8">
      <h1 className="mb-1 font-display text-2xl text-parchment">Sessions</h1>
      <p className="mb-6 text-sm text-dust">Recent conversations across every agent.</p>

      <div className="overflow-x-auto rounded-xl border border-ink-border">
        <table className="w-full min-w-[760px] text-left text-sm">
          <thead>
            <tr className="border-b border-ink-border text-xs uppercase tracking-wide text-dust/70">
              <th className="px-4 py-3 font-medium">Agent</th>
              <th className="px-4 py-3 font-medium">Visitor</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Messages</th>
              <th className="px-4 py-3 font-medium">Last activity</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.session_id} className="border-b border-ink-border/60 last:border-0">
                <td className="px-4 py-3 text-parchment">{r.agent_brand || r.agent_key}</td>
                <td className="px-4 py-3 text-dust-light">{r.customer_name || r.customer_contact || "Anonymous"}</td>
                <td className="px-4 py-3 capitalize text-dust-light">{r.conversation_status.replace(/_/g, " ")}</td>
                <td className="px-4 py-3 tabular-nums text-dust-light">{r.message_count}</td>
                <td className="px-4 py-3 text-dust-light">{new Date(r.last_activity_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
