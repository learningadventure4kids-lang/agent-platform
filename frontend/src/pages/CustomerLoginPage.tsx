import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useCustomerAuth } from "../hooks/useCustomerAuth";
import { Button } from "../components/ui/Button";

export function CustomerLoginPage() {
  const { login, error, busy } = useCustomerAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    // Logging in here is also what gets a customer into the admin screen
    // (Agents, Sessions, Leads, etc, scoped to their own agents) -- see
    // hooks/useAdminAuth.ts, which recognizes this same session.
    if (await login(email, password)) navigate("/agents");
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2">
          <Sparkles size={20} className="text-brass-light" />
          <span className="font-display text-lg text-parchment">Aria</span>
        </Link>
        <div className="rounded-2xl border border-ink-border bg-ink-soft p-6">
          <h1 className="mb-1 font-display text-xl text-parchment">Welcome back</h1>
          <p className="mb-6 text-sm text-dust">Sign in to manage your agents.</p>
          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-dust">Email</label>
              <input
                className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                required placeholder="you@example.com" autoFocus
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-dust">Password</label>
              <input
                className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                required placeholder="Your password"
              />
            </div>
            {error && <p className="text-sm text-red-300">{error}</p>}
            <Button type="submit" disabled={busy} className="w-full justify-center">
              {busy ? "Signing in..." : "Sign in"}
            </Button>
          </form>
        </div>
        <p className="mt-4 text-center text-sm text-dust">
          New here?{" "}
          <Link to="/signup" className="text-brass-light hover:underline">
            Create an account
          </Link>
        </p>
        <p className="mt-2 text-center text-xs text-dust/70">
          Platform operator?{" "}
          <Link to="/admin" className="hover:text-dust hover:underline">
            Sign in here
          </Link>
        </p>
      </div>
    </div>
  );
}
