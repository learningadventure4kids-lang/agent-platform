import { useEffect, useState } from "react";
import { useAdminAuth } from "../hooks/useAdminAuth";
import * as api from "../api/client";
import type { Tool } from "../types";
import { clsx } from "../utils/clsx";

const RISK_STYLES: Record<string, string> = {
  low: "bg-white/5 text-dust border-white/10",
  medium: "bg-brass/15 text-brass-light border-brass/30",
  high: "bg-red-500/10 text-red-300 border-red-500/30",
};

export function ToolsPage() {
  const { adminKey } = useAdminAuth();
  const [tools, setTools] = useState<Tool[]>([]);

  useEffect(() => {
    if (adminKey) api.listTools(adminKey).then(setTools);
  }, [adminKey]);

  return (
    <div className="mx-auto max-w-3xl px-6 py-8">
      <h1 className="mb-1 font-display text-2xl text-parchment">Tool catalog</h1>
      <p className="mb-6 text-sm text-dust">
        Every tool an agent could be granted. Enable/disable per agent from that agent's page.
        Confirmation-required tools are denied by the orchestration layer unless the model's call
        includes <code>confirmed: true</code> -- see that agent's Tool Activity log for denials.
      </p>
      <div className="space-y-2">
        {tools.map((t) => (
          <div key={t.tool_key} className="rounded-xl border border-ink-border bg-ink-soft p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-parchment">{t.name}</p>
              <div className="flex flex-wrap items-center gap-1.5">
                {t.category && (
                  <span className="inline-flex items-center rounded-full border border-ink-border bg-white/5 px-2.5 py-0.5 text-xs capitalize text-dust">
                    {t.category.replace(/_/g, " ")}
                  </span>
                )}
                {t.risk_level && (
                  <span
                    className={clsx(
                      "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs capitalize",
                      RISK_STYLES[t.risk_level] || RISK_STYLES.low
                    )}
                  >
                    {t.risk_level} risk
                  </span>
                )}
                {t.requires_confirmation && (
                  <span className="inline-flex items-center rounded-full border border-brass/30 bg-brass/15 px-2.5 py-0.5 text-xs text-brass-light">
                    requires confirmation
                  </span>
                )}
              </div>
            </div>
            <p className="text-xs text-dust">{t.tool_key}</p>
            <p className="mt-1 text-sm text-dust-light">{t.description}</p>
            {t.timeout_seconds != null && (
              <p className="mt-1 text-xs text-dust">timeout: {t.timeout_seconds}s</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
