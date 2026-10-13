export function AriaSuggestions({
  suggestions,
  accent,
  onPick,
}: {
  suggestions: string[];
  accent: string;
  onPick: (text: string) => void;
}) {
  if (!suggestions.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5 px-3 pb-2">
      {suggestions.map((s) => (
        <button
          key={s}
          onClick={() => onPick(s)}
          className="rounded-full border px-3 py-1 text-xs text-dust-light transition-colors hover:text-parchment"
          style={{ borderColor: "rgba(255,255,255,0.12)" }}
          onMouseEnter={(e) => (e.currentTarget.style.borderColor = `${accent}66`)}
          onMouseLeave={(e) => (e.currentTarget.style.borderColor = "rgba(255,255,255,0.12)")}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
