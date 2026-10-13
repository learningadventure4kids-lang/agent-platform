import { useEffect, useRef, useState } from "react";
import { AlertCircle } from "lucide-react";
import { useAriaChat } from "./useAriaChat";
import { AriaHeader } from "./components/AriaHeader";
import { AriaAvatar } from "./components/AriaAvatar";
import { AriaMessage } from "./components/AriaMessage";
import { TypingIndicator } from "./components/TypingIndicator";
import { AriaSuggestions } from "./components/AriaSuggestions";
import { AriaInput } from "./components/AriaInput";
import { AriaLauncher } from "./components/AriaLauncher";
import { LeadCapture } from "./components/LeadCapture";

export interface AriaChatWidgetProps {
  agentToken: string;
  apiUrl: string;
  /** Renders its own floating launcher button + panel. If false, the widget
   * fills its mount container instead (for embedding inline in a page). */
  floating?: boolean;
}

type ViewState = "closed" | "open";

export function AriaChatWidget({ agentToken, apiUrl, floating = false }: AriaChatWidgetProps) {
  const {
    agent,
    messages,
    loading,
    sending,
    error,
    isReturning,
    leadJustCreated,
    sendMessage,
    dismissReturning,
  } = useAriaChat(apiUrl, agentToken);

  const [view, setView] = useState<ViewState>(floating ? "closed" : "open");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, sending]);

  const accent = (agent?.theme?.accent as string) || "#C08A3E";
  const showPrompts = !loading && messages.length <= 1 && !isReturning;

  if (floating && view === "closed") {
    return <AriaLauncher accent={accent} onClick={() => setView("open")} />;
  }

  const panelClasses = floating
    ? "fixed bottom-4 right-4 z-50 flex h-[560px] w-[360px] max-w-[calc(100vw-2rem)] max-h-[calc(100vh-2rem)] flex-col overflow-hidden rounded-2xl border border-white/10 bg-ink shadow-2xl aria-widget-panel"
    : "flex h-full w-full flex-col overflow-hidden rounded-2xl border border-white/10 bg-ink";

  return (
    <div className={panelClasses}>
      <AriaHeader
        name={agent?.name || "Assistant"}
        brand={agent?.brand || ""}
        accent={accent}
        onMinimize={() => floating && setView("closed")}
        onClose={() => floating && setView("closed")}
      />

      <div className="scrollbar-thin flex-1 space-y-3 overflow-y-auto px-3 py-4">
        {loading && <p className="text-sm text-dust">Connecting…</p>}

        {isReturning && (
          <button
            onClick={dismissReturning}
            className="w-full rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-left text-xs text-dust-light"
          >
            Welcome back 👋 Tap to continue where you left off.
          </button>
        )}

        {messages.map((m, i) => (
          <div key={i} className="flex gap-2">
            {m.role === "assistant" && <AriaAvatar accent={accent} />}
            <div className="flex-1">
              <AriaMessage message={m} accent={accent} />
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex gap-2">
            <AriaAvatar accent={accent} />
            <TypingIndicator />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="mx-3 mb-2 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-300">
          <AlertCircle size={13} /> {error}
        </div>
      )}

      {leadJustCreated && <LeadCapture accent={accent} />}

      {showPrompts && agent && (
        <AriaSuggestions suggestions={agent.suggestions} accent={accent} onPick={sendMessage} />
      )}

      <AriaInput accent={accent} disabled={sending || loading} onSend={sendMessage} />
    </div>
  );
}
