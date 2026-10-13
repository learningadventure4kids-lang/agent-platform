import { clsx } from "../../utils/clsx";

const STYLES: Record<string, string> = {
  new: "bg-plum/30 text-dust-light border-plum/40",
  collecting_information: "bg-plum/30 text-dust-light border-plum/40",
  qualified: "bg-brass/15 text-brass-light border-brass/30",
  contacted: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  converted: "bg-emerald-500/20 text-emerald-200 border-emerald-500/40",
  closed: "bg-white/5 text-dust border-white/10",
  enabled: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  disabled: "bg-white/5 text-dust border-white/10",
  pending: "bg-plum/30 text-dust-light border-plum/40",
  processing: "bg-brass/15 text-brass-light border-brass/30",
  ready: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  failed: "bg-red-500/10 text-red-300 border-red-500/30",
  success: "bg-emerald-500/10 text-emerald-300 border-emerald-500/30",
  denied: "bg-brass/15 text-brass-light border-brass/30",
  error: "bg-red-500/10 text-red-300 border-red-500/30",
  timeout: "bg-red-500/10 text-red-300 border-red-500/30",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs capitalize",
        STYLES[status] || "bg-white/5 text-dust border-white/10"
      )}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
