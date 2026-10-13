import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, LayoutDashboard, Plus } from "lucide-react";
import { useCustomerAuth } from "../hooks/useCustomerAuth";
import * as api from "../api/customer";
import type { BuilderAgent } from "../types";
import { Button } from "../components/ui/Button";
import { StatusBadge } from "../components/ui/StatusBadge";

export function DashboardPage() {
  const { sessionToken, user } = useCustomerAuth();
  const [agents, setAgents] = useState<BuilderAgent[] | null>(null);

  useEffect(() => {
    if (sessionToken) api.listMyAgents(sessionToken).then(setAgents);
  }, [sessionToken]);

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="font-display text-2xl text-parchment">
            {user?.company_name ? `${user.company_name}'s agents` : "Your agents"}
          </h1>
          <p className="mt-1 text-sm text-dust">Every assistant you've built, and its embed script.</p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/agents">
            <Button variant="secondary" className="gap-1.5">
              <LayoutDashboard size={16} /> Full admin view
            </Button>
          </Link>
          <Link to="/dashboard/new">
            <Button className="gap-1.5">
              <Plus size={16} /> New agent
            </Button>
          </Link>
        </div>
      </div>

      {agents === null ? (
        <p className="text-sm text-dust">Loading...</p>
      ) : agents.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-ink-border bg-ink-soft p-12 text-center">
          <p className="mb-4 text-sm text-dust">You haven't created an agent yet.</p>
          <Link to="/dashboard/new">
            <Button className="gap-1.5">
              <Plus size={16} /> Create your first agent
            </Button>
          </Link>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {agents.map((a) => (
            <Link
              key={a.id}
              to={`/dashboard/agents/${a.id}`}
              className="group rounded-2xl border border-ink-border bg-ink-soft p-5 transition-colors hover:border-brass/40"
            >
              <div className="flex items-center justify-between">
                <p className="font-display text-lg text-parchment">{a.name}</p>
                <StatusBadge status={a.enabled ? "enabled" : "disabled"} />
              </div>
              <p className="text-sm text-dust">{a.brand_name}</p>
              <p className="mt-3 line-clamp-2 text-xs text-dust/80">{a.welcome_message}</p>
              <div className="mt-4 flex items-center gap-1 text-xs text-brass-light opacity-0 transition-opacity group-hover:opacity-100">
                Manage <ArrowRight size={12} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
