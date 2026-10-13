import { useRef, useState, type FormEvent } from "react";
import { Bot, Send, Sparkles, User } from "lucide-react";
import * as api from "../api/customer";
import { Button } from "./ui/Button";

interface PreviewMessage {
  role: "assistant" | "user";
  content: string;
}

interface AgentPreviewChatProps {
  sessionToken: string;
  agentId: number;
  name: string;
  brandName: string;
  welcomeMessage: string;
  suggestions: string[];
  accentColor?: string;
}

/**
 * A real, working chat panel embedded in the dashboard so a customer can
 * see exactly what a visitor to their site would experience -- before (or
 * any time after) copying the embed script anywhere. It talks to
 * `/api/builder/agents/{id}/preview-chat`, which runs the identical
 * LangGraph pipeline the public widget uses, just authenticated by the
 * customer's own dashboard session instead of the plaintext public token
 * (which isn't available here after the first reveal). This is why a
 * reply can take a moment and can occasionally show the same friendly
 * fallback message a real visitor would see -- it's a live run, not a
 * canned mockup.
 */
export function AgentPreviewChat({
  sessionToken, agentId, name, brandName, welcomeMessage, suggestions, accentColor,
}: AgentPreviewChatProps) {
  const accent = accentColor || "#C08A3E";
  const [messages, setMessages] = useState<PreviewMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  };

  const send = async (text: string) => {
    const message = text.trim();
    if (!message || sending) return;
    setError(null);
    setMessages((m) => [...m, { role: "user", content: message }]);
    setInput("");
    setSending(true);
    scrollToBottom();
    try {
      const result = await api.previewMyAgentChat(sessionToken, agentId, {
        message,
        session_id: sessionId,
      });
      setSessionId(result.session_id);
      setMessages((m) => [...m, { role: "assistant", content: result.response }]);
    } catch (err) {
      setError(err instanceof api.ApiError ? err.message : "Couldn't reach the preview agent.");
    } finally {
      setSending(false);
      scrollToBottom();
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    send(input);
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-ink-border bg-ink-soft">
      <div className="flex items-center gap-2 border-b border-ink-border px-5 py-3" style={{ backgroundColor: `${accent}1a` }}>
        <span
          className="flex h-7 w-7 items-center justify-center rounded-full text-ink"
          style={{ backgroundColor: accent }}
        >
          <Bot size={15} />
        </span>
        <div className="leading-tight">
          <p className="text-sm font-medium text-parchment">{name}</p>
          <p className="text-xs text-dust">{brandName}</p>
        </div>
      </div>

      <div ref={scrollRef} className="scrollbar-thin h-80 overflow-y-auto px-4 py-4">
        <div className="mb-3 flex items-start gap-2">
          <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-ink text-dust">
            <Bot size={13} />
          </span>
          <div className="max-w-[85%] rounded-xl rounded-tl-sm bg-ink px-3 py-2 text-sm text-parchment-dim">
            {welcomeMessage}
          </div>
        </div>

        {messages.map((m, i) => (
          <div
            key={i}
            className={`mb-3 flex items-start gap-2 ${m.role === "user" ? "flex-row-reverse" : ""}`}
          >
            <span
              className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
                m.role === "user" ? "text-ink" : "bg-ink text-dust"
              }`}
              style={m.role === "user" ? { backgroundColor: accent } : undefined}
            >
              {m.role === "user" ? <User size={13} /> : <Bot size={13} />}
            </span>
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                m.role === "user"
                  ? "rounded-tr-sm text-ink"
                  : "rounded-tl-sm bg-ink text-parchment-dim"
              }`}
              style={m.role === "user" ? { backgroundColor: accent } : undefined}
            >
              {m.content}
            </div>
          </div>
        ))}

        {sending && (
          <div className="flex items-center gap-2 text-xs text-dust">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-ink">
              <Bot size={13} />
            </span>
            Typing...
          </div>
        )}

        {messages.length === 0 && suggestions.length > 0 && (
          <div className="mt-1 flex flex-wrap gap-1.5">
            {suggestions.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="flex items-center gap-1 rounded-full border border-ink-border bg-ink px-2.5 py-1 text-xs text-dust hover:border-brass/40 hover:text-parchment"
              >
                <Sparkles size={11} /> {s}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && <p className="px-4 pb-2 text-xs text-red-300">{error}</p>}

      <form onSubmit={submit} className="flex items-center gap-2 border-t border-ink-border p-3">
        <input
          className="input flex-1"
          placeholder="Try saying something a real visitor might ask..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
        />
        <Button type="submit" size="sm" disabled={sending || !input.trim()} className="gap-1.5">
          <Send size={14} />
        </Button>
      </form>
    </div>
  );
}
