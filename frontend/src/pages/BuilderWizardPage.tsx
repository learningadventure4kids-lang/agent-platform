import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft, ArrowRight, Bed, Briefcase, Gem, GraduationCap, Home as HomeIcon,
  Sparkle, Sparkles, Stethoscope, Utensils, Wand2, type LucideIcon,
} from "lucide-react";
import { useCustomerAuth } from "../hooks/useCustomerAuth";
import * as api from "../api/customer";
import type { Persona } from "../types";
import { Button } from "../components/ui/Button";
import { clsx } from "../utils/clsx";

const ICONS: Record<string, LucideIcon> = {
  gem: Gem, home: HomeIcon, sparkles: Sparkles, stethoscope: Stethoscope, sparkle: Sparkle,
  bed: Bed, utensils: Utensils, "graduation-cap": GraduationCap, briefcase: Briefcase, wand: Wand2,
};

const ACCENT_COLORS = ["#C08A3E", "#7C5CFF", "#2FA86B", "#D1495B", "#2E8FBF", "#B5862C"];

export function BuilderWizardPage() {
  const { sessionToken } = useCustomerAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(0);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [personaKey, setPersonaKey] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [brandName, setBrandName] = useState("");
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [accentColor, setAccentColor] = useState(ACCENT_COLORS[0]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listPersonas().then(setPersonas);
  }, []);

  const persona = personas.find((p) => p.key === personaKey) || null;

  const createAgent = async () => {
    if (!sessionToken || !persona) return;
    setSubmitting(true);
    setError(null);
    try {
      const snippet = await api.createMyAgent(sessionToken, {
        persona_key: persona.key,
        name: name.trim(),
        brand_name: brandName.trim(),
        welcome_message: welcomeMessage.trim() || undefined,
        accent_color: accentColor,
      });
      navigate(`/dashboard/agents/${snippet.agent_id}`, { state: { freshSnippet: snippet } });
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Could not create your agent.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-8 flex items-center gap-2 text-xs text-dust">
        {["Persona", "Details", "Review"].map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <span
              className={clsx(
                "flex h-6 w-6 items-center justify-center rounded-full border text-xs",
                i <= step ? "border-brass/60 bg-brass/15 text-brass-light" : "border-ink-border text-dust"
              )}
            >
              {i + 1}
            </span>
            <span className={i <= step ? "text-parchment" : ""}>{label}</span>
            {i < 2 && <span className="mx-1 text-dust/40">—</span>}
          </div>
        ))}
      </div>

      {step === 0 && (
        <div>
          <h1 className="mb-1 font-display text-2xl text-parchment">What kind of business is this for?</h1>
          <p className="mb-6 text-sm text-dust">
            Pick the closest match -- you can change everything afterward.
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            {personas.map((p) => {
              const Icon = ICONS[p.icon] || Wand2;
              const selected = p.key === personaKey;
              return (
                <button
                  key={p.key}
                  onClick={() => setPersonaKey(p.key)}
                  className={clsx(
                    "flex flex-col items-start rounded-2xl border p-5 text-left transition-colors",
                    selected ? "border-brass/60 bg-brass/10" : "border-ink-border bg-ink-soft hover:border-brass/30"
                  )}
                >
                  <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-brass/15 text-brass-light">
                    <Icon size={18} />
                  </div>
                  <p className="font-medium text-parchment">{p.label}</p>
                  <p className="mt-1 text-sm text-dust">{p.blurb}</p>
                  {!p.specialized && (
                    <span className="mt-2 text-xs text-dust/70">Lead capture + knowledge base</span>
                  )}
                </button>
              );
            })}
          </div>
          <div className="mt-8 flex justify-end">
            <Button disabled={!personaKey} onClick={() => setStep(1)} className="gap-1.5">
              Continue <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      )}

      {step === 1 && persona && (
        <div>
          <h1 className="mb-1 font-display text-2xl text-parchment">Make it yours</h1>
          <p className="mb-6 text-sm text-dust">You'll be able to edit all of this later.</p>
          <div className="space-y-4 rounded-2xl border border-ink-border bg-ink-soft p-6">
            <div>
              <label className="mb-1 block text-xs text-dust">Your business name</label>
              <input className="input" value={brandName} onChange={(e) => setBrandName(e.target.value)} placeholder="Acme Co" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-dust">Assistant's name</label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Aria" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-dust">Welcome message (optional)</label>
              <textarea
                className="input" rows={2} value={welcomeMessage}
                onChange={(e) => setWelcomeMessage(e.target.value)}
                placeholder={persona.welcome_message}
              />
            </div>
            <div>
              <label className="mb-1 block text-xs text-dust">Accent color</label>
              <div className="flex gap-2">
                {ACCENT_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setAccentColor(c)}
                    className={clsx(
                      "h-7 w-7 rounded-full border-2",
                      accentColor === c ? "border-parchment" : "border-transparent"
                    )}
                    style={{ backgroundColor: c }}
                    aria-label={c}
                  />
                ))}
              </div>
            </div>
          </div>
          <div className="mt-8 flex justify-between">
            <Button variant="secondary" onClick={() => setStep(0)} className="gap-1.5">
              <ArrowLeft size={16} /> Back
            </Button>
            <Button disabled={!brandName.trim() || !name.trim()} onClick={() => setStep(2)} className="gap-1.5">
              Continue <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      )}

      {step === 2 && persona && (
        <div>
          <h1 className="mb-1 font-display text-2xl text-parchment">Review & generate</h1>
          <p className="mb-6 text-sm text-dust">
            This creates your agent and gives you a script to paste into your site.
          </p>
          <div className="space-y-3 rounded-2xl border border-ink-border bg-ink-soft p-6 text-sm">
            <Row label="Persona" value={persona.label} />
            <Row label="Business" value={brandName} />
            <Row label="Assistant name" value={name} />
            <Row label="Tools granted" value={persona.specialized ? "Specialized + lead capture + knowledge base" : "Lead capture + knowledge base"} />
          </div>
          {error && <p className="mt-4 text-sm text-red-300">{error}</p>}
          <div className="mt-8 flex justify-between">
            <Button variant="secondary" onClick={() => setStep(1)} className="gap-1.5">
              <ArrowLeft size={16} /> Back
            </Button>
            <Button onClick={createAgent} disabled={submitting} className="gap-1.5">
              {submitting ? "Generating..." : "Generate my agent"} <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between border-b border-ink-border/60 pb-2 last:border-0 last:pb-0">
      <span className="text-dust">{label}</span>
      <span className="font-medium text-parchment">{value}</span>
    </div>
  );
}
