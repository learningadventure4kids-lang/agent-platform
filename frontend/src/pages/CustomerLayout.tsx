import { NavLink, Navigate, Outlet } from "react-router-dom";
import {
  BarChart3, Bot, LogOut, MessagesSquare, Plus, Sparkles, Target, Users, Wrench,
} from "lucide-react";
import { useCustomerAuth } from "../hooks/useCustomerAuth";
import { clsx } from "../utils/clsx";

const NAV = [
  { to: "/dashboard", label: "My Agents", icon: Bot, end: true },
  { to: "/dashboard/tools", label: "Tools", icon: Wrench },
  { to: "/dashboard/sessions", label: "Sessions", icon: MessagesSquare },
  { to: "/dashboard/customers", label: "Customers", icon: Users },
  { to: "/dashboard/leads", label: "Leads", icon: Target },
  { to: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
];

/** This customer's own version of the admin screen (see AdminLayout) --
 * every route behind it calls the /api/builder/* endpoints, which are
 * hard-scoped server-side to this user's own agents (app/api/builder.py).
 * Deliberately left out, by design, not by omission: AI Providers (shared
 * platform infrastructure holding other tenants' API keys) and Settings
 * (platform env-var configuration) -- neither is "this customer's own
 * data" the way agents/tools/sessions/customers/leads are. */
export function CustomerLayout() {
  const { isAuthenticated, user, logout } = useCustomerAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <div className="flex h-screen">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-ink-border bg-ink/60 px-3 py-5 sm:flex">
        <NavLink to="/dashboard" className="mb-1 flex items-center gap-2 px-2 font-display text-lg text-parchment">
          <Sparkles size={18} className="text-brass-light" /> Aria
        </NavLink>
        <p className="mb-5 truncate px-2 text-xs text-dust/70">{user?.company_name || user?.email}</p>
        <NavLink
          to="/dashboard/new"
          className={({ isActive }) =>
            clsx(
              "mb-4 flex items-center justify-center gap-1.5 rounded-lg bg-brass/15 px-3 py-2 text-sm text-brass-light hover:bg-brass/25",
              isActive && "bg-brass/25"
            )
          }
        >
          <Plus size={15} /> New agent
        </NavLink>
        <nav className="flex-1 space-y-1">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive ? "bg-brass/15 text-brass-light" : "text-dust hover:bg-white/5 hover:text-parchment"
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={logout}
          className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-dust hover:bg-white/5 hover:text-parchment"
        >
          <LogOut size={16} /> Sign out
        </button>
      </aside>
      <main className="scrollbar-thin flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}
