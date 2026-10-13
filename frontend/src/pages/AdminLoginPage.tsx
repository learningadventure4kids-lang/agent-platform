import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import { Button } from "../components/ui/Button";

export function AdminLoginPage() {
  const { login, loggingIn, error, principalKind } = useAdminAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const navigate = useNavigate();

  // A customer who signed in at /login is already allowed onto the admin
  // screen (scoped to their own agents) -- no reason to show them the
  // platform-operator login form too.
  if (principalKind === "customer") return <Navigate to="/agents" replace />;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (await login(username, password)) navigate("/agents");
  };

  return (
    <div className="flex h-full items-center justify-center px-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm rounded-2xl border border-ink-border bg-ink-soft p-7">
        <div className="mb-6 flex items-center gap-2.5">
          <Sparkles size={18} className="text-brass" />
          <h1 className="font-display text-lg text-parchment">Aria Platform Admin</h1>
        </div>

        <label className="mb-1 block text-xs text-dust">Username</label>
        <input
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="mb-4 w-full rounded-lg border border-ink-border bg-ink px-3 py-2 text-sm text-parchment focus:border-brass/50 focus:outline-none"
          autoComplete="username"
        />

        <label className="mb-1 block text-xs text-dust">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="mb-5 w-full rounded-lg border border-ink-border bg-ink px-3 py-2 text-sm text-parchment focus:border-brass/50 focus:outline-none"
          autoComplete="current-password"
        />

        {error && <p className="mb-4 text-sm text-red-300">{error}</p>}

        <Button type="submit" disabled={loggingIn} className="w-full">
          {loggingIn ? "Signing in…" : "Sign in"}
        </Button>
      </form>
    </div>
  );
}
