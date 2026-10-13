import { NavLink, Navigate, Outlet } from "react-router-dom";
import { BarChart3, Bot, Cpu, LogOut, Settings, Users, Wrench, MessagesSquare, Target } from "lucide-react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import { clsx } from "../utils/clsx";

// Providers (holds the platform's real AI-provider API keys) and Settings
// (platform-wide config) are platform-operator-only -- a self-serve
// customer gets every other section, scoped to just their own agents.
const NAV = [
  { to: "/agents", label: "Agents", icon: Bot },
  { to: "/providers", label: "AI Providers", icon: Cpu, adminOnly: true },
  { to: "/tools", label: "Tools", icon: Wrench },
  { to: "/sessions", label: "Sessions", icon: MessagesSquare },
  { to: "/customers", label: "Customers", icon: Users },
  { to: "/leads", label: "Leads", icon: Target },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/settings", label: "Settings", icon: Settings, adminOnly: true },
];

export function AdminLayout() {
  const { isAuthenticated, principalKind, logout } = useAdminAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const nav = NAV.filter((item) => !item.adminOnly || principalKind === "admin");

  return (
    <div className="flex h-full">
      <aside className="hidden w-56 shrink-0 flex-col border-r border-ink-border bg-ink/60 px-3 py-5 sm:flex">
        <div className="mb-6 px-2 font-display text-lg text-parchment">✦ Aria Platform</div>
        <nav className="flex-1 space-y-1">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
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
