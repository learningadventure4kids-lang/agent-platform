export interface AgentPublicInfo {
  name: string;
  brand: string;
  welcome_message: string;
  suggestions: string[];
  theme: Record<string, unknown>;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

export interface SessionState {
  session_id: string;
  agent: AgentPublicInfo;
  conversation_status: string;
  is_returning: boolean;
  messages: ChatMessage[];
}

export interface ChatResponse {
  session_id: string;
  agent: AgentPublicInfo;
  response: string;
  message_id: number;
  lead_created: boolean;
}

export class WidgetApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

/** Same normalization as the admin dashboard's client.ts (kept as an
 * independent copy since this file ships standalone, bundled into
 * aria-widget.js): FastAPI's 422 responses put an ARRAY of validation
 * errors in `detail`, not a string. Passing that straight into
 * `Error(message)` gets coerced to the useless string "[object Object]". */
function extractErrorDetail(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object" || !("detail" in body)) return fallback;
  const detail = (body as { detail: unknown }).detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        return String((item as { msg: unknown }).msg);
      }
      return typeof item === "string" ? item : JSON.stringify(item);
    });
    return messages.join("; ") || fallback;
  }

  if (detail && typeof detail === "object") {
    try {
      return JSON.stringify(detail);
    } catch {
      return fallback;
    }
  }

  return fallback;
}

export class AriaApiClient {
  constructor(private apiUrl: string, private agentToken: string) {}

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    let res: Response;
    try {
      res = await fetch(`${this.apiUrl}${path}`, {
        ...options,
        // See the identical comment in the admin dashboard's api/client.ts
        // -- this must be spread AFTER `...options`, or a caller's own
        // `headers` option silently wipes out the Content-Type default.
        headers: { "Content-Type": "application/json", ...options.headers },
      });
    } catch {
      throw new WidgetApiError("Can't reach the server right now.", 0);
    }
    if (!res.ok) {
      let detail = "Something went wrong.";
      try {
        detail = extractErrorDetail(await res.json(), detail);
      } catch {
        /* ignore */
      }
      throw new WidgetApiError(detail, res.status);
    }
    return res.json() as Promise<T>;
  }

  createSession(): Promise<SessionState> {
    return this.request("/api/session", {
      method: "POST",
      body: JSON.stringify({ agent_token: this.agentToken }),
    });
  }

  getSession(sessionId: string): Promise<SessionState> {
    return this.request(`/api/session/${sessionId}`);
  }

  sendMessage(message: string, sessionId?: string): Promise<ChatResponse> {
    return this.request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ agent_token: this.agentToken, session_id: sessionId, message }),
    });
  }
}
