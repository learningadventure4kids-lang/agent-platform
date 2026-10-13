import { Minus, X } from "lucide-react";

export function AriaHeader({
  name,
  brand,
  accent,
  onMinimize,
  onClose,
}: {
  name: string;
  brand: string;
  accent: string;
  onMinimize: () => void;
  onClose: () => void;
}) {
  return (
    <div
      className="flex items-center justify-between border-b border-white/10 px-4 py-3"
      style={{ background: `linear-gradient(135deg, ${accent}22, transparent)` }}
    >
      <div>
        <p className="text-sm font-semibold text-parchment">{name}</p>
        <p className="text-xs text-dust">{brand}</p>
      </div>
      <div className="flex items-center gap-1">
        <button onClick={onMinimize} aria-label="Minimize" className="rounded-full p-1.5 text-dust hover:bg-white/10 hover:text-parchment">
          <Minus size={14} />
        </button>
        <button onClick={onClose} aria-label="Close" className="rounded-full p-1.5 text-dust hover:bg-white/10 hover:text-parchment">
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
