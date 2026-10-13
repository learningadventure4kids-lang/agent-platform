import type { ChatMessage } from "../api";

export function AriaMessage({ message, accent }: { message: ChatMessage; accent: string }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex gap-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-3.5 py-2 text-sm leading-relaxed ${
          isUser ? "rounded-tr-sm text-ink" : "rounded-tl-sm border border-white/10 bg-white/5 text-parchment"
        }`}
        style={isUser ? { backgroundColor: accent } : undefined}
      >
        {message.content.split("\n").map((line, i) => (
          <p key={i} className={i > 0 ? "mt-1.5" : undefined}>
            {line}
          </p>
        ))}
      </div>
    </div>
  );
}
