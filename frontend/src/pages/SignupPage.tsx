import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import { useCustomerAuth } from "../hooks/useCustomerAuth";
import { Button } from "../components/ui/Button";

export function SignupPage() {
  const { signup, error, busy } = useCustomerAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [companyName, setCompanyName] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const ok = await signup({ email, password, name, company_name: companyName || undefined });
    if (ok) navigate("/dashboard/new");
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm">
        <Link to="/" className="mb-8 flex items-center justify-center gap-2">
          <Sparkles size={20} className="text-brass-light" />
          <span className="font-display text-lg text-parchment">Aria</span>
        </Link>
        <div className="rounded-2xl border border-ink-border bg-ink-soft p-6">
          <h1 className="mb-1 font-display text-xl text-parchment">Create your account</h1>
          <p className="mb-6 text-sm text-dust">Build your first AI agent in a couple of minutes.</p>
          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs text-dust">Your name</label>
              <input
                className="input" value={name} onChange={(e) => setName(e.target.value)}
                required placeholder="Jordan Lee"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-dust">Business name (optional)</label>
              <input
                className="input" value={companyName} onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Acme Co"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-dust">Email</label>
              <input
                className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                required placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-dust">Password</label>
              <input
                className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                required minLength={8} placeholder="At least 8 characters"
              />
            </div>
            {error && <p className="text-sm text-red-300">{error}</p>}
            <Button type="submit" disabled={busy} className="w-full justify-center">
              {busy ? "Creating account..." : "Create account"}
            </Button>
          </form>
        </div>
        <p className="mt-4 text-center text-sm text-dust">
          Already have an account?{" "}
          <Link to="/login" className="text-brass-light hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
