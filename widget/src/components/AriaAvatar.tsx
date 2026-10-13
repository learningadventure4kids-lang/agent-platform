export function AriaAvatar({ accent = "#C08A3E" }: { accent?: string }) {
  return (
    <div
      className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-sm"
      style={{ borderColor: `${accent}55`, backgroundColor: `${accent}22`, color: accent }}
    >
      ✦
    </div>
  );
}
