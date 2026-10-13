import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Check, Gem, Home as HomeIcon, Sparkles } from "lucide-react";
import { Button } from "../components/ui/Button";

const STEPS = [
  {
    title: "Pick a persona",
    body: "Jewellery, real estate, astrology, a clinic, a salon -- start from a template built for your business, or a blank one.",
  },
  {
    title: "Make it yours",
    body: "Name your assistant, set your brand, upload your FAQs and documents so it answers from your own knowledge.",
  },
  {
    title: "Get your script",
    body: "One line of code. Paste it into your site and your assistant is live -- capturing leads from the first conversation.",
  },
];

const FEATURES = [
  "Lead capture built in, with confirmation before anything is saved",
  "Your own knowledge base -- upload docs and it answers from them, not guesses",
  "Specialized tools for jewellery, real estate, and astrology verticals",
  "Full audit log of every action your agent takes, for every conversation",
  "Swap AI providers (Ollama, Groq, OpenAI-compatible) without rebuilding anything",
  "One script tag -- no React, no build step, works on any website",
];

export function LandingPage() {
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <Sparkles size={20} className="text-brass-light" />
          <span className="font-display text-lg text-parchment">Aria</span>
        </div>
        <nav className="flex items-center gap-3">
          <Link to="/login" className="text-sm text-dust hover:text-parchment">
            Sign in
          </Link>
          <Link to="/signup">
            <Button size="sm">Get started</Button>
          </Link>
        </nav>
      </header>

      <main className="mx-auto max-w-6xl px-6">
        <section className="py-20 text-center">
          <p className="mb-4 text-xs uppercase tracking-[0.2em] text-brass-light">
            Build your own AI agent
          </p>
          <h1 className="mx-auto max-w-3xl font-display text-4xl leading-tight text-parchment sm:text-5xl">
            An AI assistant for your business, live on your site in minutes
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base text-dust-light">
            Pick a persona, add your knowledge, and get a single script tag to paste into your
            website. No code, no React, no separate app to manage.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link to="/signup">
              <Button className="gap-2">
                Start building free <ArrowRight size={16} />
              </Button>
            </Link>
            <a href="#how-it-works" className="text-sm text-dust hover:text-parchment">
              See how it works
            </a>
          </div>
        </section>

        <section id="how-it-works" className="grid gap-6 py-16 sm:grid-cols-3">
          {STEPS.map((s, i) => (
            <div key={s.title} className="rounded-2xl border border-ink-border bg-ink-soft p-6">
              <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-brass/15 text-sm font-medium text-brass-light">
                {i + 1}
              </div>
              <h3 className="mb-2 font-display text-lg text-parchment">{s.title}</h3>
              <p className="text-sm text-dust-light">{s.body}</p>
            </div>
          ))}
        </section>

        <section className="py-16">
          <div className="mb-8 text-center">
            <h2 className="font-display text-2xl text-parchment">Built for real conversations, not demos</h2>
            <p className="mt-2 text-sm text-dust">
              Every agent runs on the same orchestration layer -- permission-checked, audited, and
              isolated from every other business on the platform.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div key={f} className="flex items-start gap-2.5 rounded-xl border border-ink-border bg-ink-soft p-4">
                <Check size={16} className="mt-0.5 shrink-0 text-brass-light" />
                <span className="text-sm text-dust-light">{f}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="py-16">
          <div className="mb-8 text-center">
            <h2 className="font-display text-2xl text-parchment">Start from a template</h2>
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <PersonaTeaser icon={<Gem size={20} />} label="Jewellery & Retail" blurb="Live catalog search and qualified leads." />
            <PersonaTeaser icon={<HomeIcon size={20} />} label="Real Estate" blurb="Live listing search and buyer leads." />
            <PersonaTeaser icon={<Sparkles size={20} />} label="Astrology & Consultation" blurb="Birth chart calculation and bookings." />
          </div>
          <p className="mt-4 text-center text-sm text-dust">
            Plus clinics, salons, hotels, restaurants, education, and professional services --{" "}
            <Link to="/signup" className="text-brass-light hover:underline">
              see all personas
            </Link>
            .
          </p>
        </section>

        <section className="py-16 text-center">
          <h2 className="font-display text-2xl text-parchment">Ready to go live?</h2>
          <p className="mt-2 text-sm text-dust">No credit card required to start.</p>
          <Link to="/signup" className="mt-6 inline-block">
            <Button className="gap-2">
              Create your agent <ArrowRight size={16} />
            </Button>
          </Link>
        </section>
      </main>

      <footer className="border-t border-ink-border py-8 text-center text-xs text-dust">
        Aria Agent Platform
      </footer>
    </div>
  );
}

function PersonaTeaser({ icon, label, blurb }: { icon: ReactNode; label: string; blurb: string }) {
  return (
    <div className="rounded-2xl border border-ink-border bg-ink-soft p-5">
      <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-brass/15 text-brass-light">
        {icon}
      </div>
      <p className="font-medium text-parchment">{label}</p>
      <p className="mt-1 text-sm text-dust">{blurb}</p>
    </div>
  );
}
