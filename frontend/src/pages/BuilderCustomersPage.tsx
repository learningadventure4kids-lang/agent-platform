import { useEffect, useState } from "react";
import { useCustomerAuth } from "../hooks/useCustomerAuth";
import * as api from "../api/customer";
import type { BuilderCustomerRow } from "../types";

export function BuilderCustomersPage() {
  const { sessionToken } = useCustomerAuth();
  const [rows, setRows] = useState<BuilderCustomerRow[]>([]);

  useEffect(() => {
    if (sessionToken) api.listMyCustomers(sessionToken).then(setRows);
  }, [sessionToken]);

  return (
    <div className="mx-auto max-w-4xl px-6 py-8">
      <h1 className="mb-1 font-display text-2xl text-parchment">Customers</h1>
      <p className="mb-6 text-sm text-dust">
        Visitors recognized across your agents' sessions -- scoped to your own agents only.
      </p>

      <div className="overflow-x-auto rounded-xl border border-ink-border">
        <table className="w-full min-w-[600px] text-left text-sm">
          <thead>
            <tr className="border-b border-ink-border text-xs uppercase tracking-wide text-dust/70">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Contact</th>
              <th className="px-4 py-3 font-medium">Sessions</th>
              <th className="px-4 py-3 font-medium">Leads</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-b border-ink-border/60 last:border-0">
                <td className="px-4 py-3 text-parchment">{r.name || "Unnamed"}</td>
                <td className="px-4 py-3 text-dust-light">{r.email || r.phone || "—"}</td>
                <td className="px-4 py-3 tabular-nums text-dust-light">{r.session_count}</td>
                <td className="px-4 py-3 tabular-nums text-dust-light">{r.lead_count}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-10 text-center text-sm text-dust">
                  No customers yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
