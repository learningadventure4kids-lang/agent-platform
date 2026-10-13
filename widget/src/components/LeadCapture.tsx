import { Check } from "lucide-react";

/** Only ever shown after a real ChatResponse.lead_created === true -- never
 * speculatively, so the widget never implies contact info was saved when it
 * wasn't. */
export function LeadCapture({ accent }: { accent: string }) {
  return (
    <div
      className="mx-3 mb-2 flex items-center gap-2 rounded-xl border px-3 py-2 text-xs"
      style={{ borderColor: `${accent}55`, backgroundColor: `${accent}15`, color: "#F6F1E6" }}
    >
      <Check size={14} style={{ color: accent }} />
      Saved -- someone from the team will follow up soon.
    </div>
  );
}
