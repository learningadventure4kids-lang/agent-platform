import { useCallback, useEffect, useRef, useState } from "react";
import { AriaApiClient, WidgetApiError, type AgentPublicInfo, type ChatMessage, type SessionState } from "./api";

function storageKey(agentToken: string) {
  // Never mix sessions between different agents -- keyed by a hash-ish
  // slice of the token rather than the full token, to avoid putting the
  // full public token in a readable localStorage key for no reason.
  return `aria_session_id_${agentToken.slice(-12)}`;
}

export function useAriaChat(apiUrl: string, agentToken: string) {
  const client = useRef(new AriaApiClient(apiUrl, agentToken));
  const [agent, setAgent] = useState<AgentPublicInfo | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isReturning, setIsReturning] = useState(false);
  const [leadJustCreated, setLeadJustCreated] = useState(false);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    (async () => {
      const key = storageKey(agentToken);
      const existingId = localStorage.getItem(key);
      try {
        let state: SessionState;
        if (existingId) {
          state = await client.current.getSession(existingId);
        } else {
          state = await client.current.createSession();
          localStorage.setItem(key, state.session_id);
        }
        setSessionId(state.session_id);
        setAgent(state.agent);
        setMessages(state.messages);
        setIsReturning(state.is_returning);
      } catch {
        localStorage.removeItem(key);
        try {
          const state = await client.current.createSession();
          localStorage.setItem(key, state.session_id);
          setSessionId(state.session_id);
          setAgent(state.agent);
          setMessages(state.messages);
        } catch (err) {
          setError(err instanceof WidgetApiError ? err.message : "Could not connect.");
        }
      } finally {
        setLoading(false);
      }
    })();
  }, [agentToken]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      setError(null);
      setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
      setSending(true);
      setLeadJustCreated(false);
      try {
        const res = await client.current.sendMessage(trimmed, sessionId || undefined);
        setSessionId(res.session_id);
        setAgent(res.agent);
        setMessages((prev) => [...prev, { role: "assistant", content: res.response }]);
        setLeadJustCreated(res.lead_created);
      } catch (err) {
        setError(err instanceof WidgetApiError ? err.message : "Something went wrong. Please try again.");
      } finally {
        setSending(false);
      }
    },
    [sessionId]
  );

  const dismissReturning = useCallback(() => setIsReturning(false), []);

  return {
    agent,
    messages,
    loading,
    sending,
    error,
    isReturning,
    leadJustCreated,
    sendMessage,
    dismissReturning,
  };
}
