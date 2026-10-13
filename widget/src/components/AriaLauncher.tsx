export function AriaLauncher({ accent, onClick }: { accent: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      aria-label="Open chat"
      className="fixed bottom-4 right-4 z-50 flex h-14 w-14 items-center justify-center rounded-full text-xl text-ink shadow-lg transition-transform hover:scale-105"
      style={{ backgroundColor: accent, boxShadow: `0 8px 24px -8px ${accent}aa` }}
    >
      ✦
    </button>
  );
}
