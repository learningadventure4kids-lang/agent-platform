export function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 rounded-2xl rounded-tl-sm border border-white/10 bg-white/5 px-3.5 py-3 w-fit">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-pulse rounded-full bg-dust-light"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  );
}
