import type {
  AgentTool, AuthResponse, BuilderAgent, BuilderCustomerRow, BuilderDocument, BuilderSessionRow,
  CustomerUser, EmbedSnippet, Lead, LeadStats, Persona, PlanInfo, PreviewChatResponse, Tool, ToolExecutionLog,
} from "../types";
import { request } from "./http";

export { ApiError } from "./http";

function authHeaders(sessionToken: string): HeadersInit {
  return { Authorization: `Bearer ${sessionToken}` };
}

export function signup(payload: {
  email: string; password: string; name: string; company_name?: string;
}): Promise<AuthResponse> {
  return request("/api/auth/signup", { method: "POST", body: JSON.stringify(payload) });
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function logout(sessionToken: string): Promise<void> {
  return request("/api/auth/logout", { method: "POST", headers: authHeaders(sessionToken) });
}

export function me(sessionToken: string): Promise<CustomerUser> {
  return request("/api/auth/me", { headers: authHeaders(sessionToken) });
}

export function listPersonas(): Promise<Persona[]> {
  return request("/api/builder/personas");
}

export function listMyAgents(sessionToken: string): Promise<BuilderAgent[]> {
  return request("/api/builder/agents", { headers: authHeaders(sessionToken) });
}

export function getMyAgent(sessionToken: string, id: number): Promise<BuilderAgent> {
  return request(`/api/builder/agents/${id}`, { headers: authHeaders(sessionToken) });
}

export function createMyAgent(
  sessionToken: string,
  payload: { persona_key: string; name: string; brand_name: string; welcome_message?: string; accent_color?: string },
): Promise<EmbedSnippet> {
  return request("/api/builder/agents", {
    method: "POST",
    headers: authHeaders(sessionToken),
    body: JSON.stringify(payload),
  });
}

export function updateMyAgent(
  sessionToken: string, id: number, payload: Record<string, unknown>,
): Promise<BuilderAgent> {
  return request(`/api/builder/agents/${id}`, {
    method: "PATCH",
    headers: authHeaders(sessionToken),
    body: JSON.stringify(payload),
  });
}

export function rotateMyAgentToken(sessionToken: string, id: number): Promise<EmbedSnippet> {
  return request(`/api/builder/agents/${id}/rotate-token`, {
    method: "POST",
    headers: authHeaders(sessionToken),
  });
}

export function listMyAgentDocuments(sessionToken: string, id: number): Promise<BuilderDocument[]> {
  return request(`/api/builder/agents/${id}/documents`, { headers: authHeaders(sessionToken) });
}

export function getMyPlan(sessionToken: string): Promise<PlanInfo> {
  return request("/api/builder/me/plan", { headers: authHeaders(sessionToken) });
}

export function previewMyAgentChat(
  sessionToken: string, id: number, payload: { message: string; session_id?: string },
): Promise<PreviewChatResponse> {
  return request(`/api/builder/agents/${id}/preview-chat`, {
    method: "POST",
    headers: authHeaders(sessionToken),
    body: JSON.stringify(payload),
  });
}

export function uploadMyAgentDocument(
  sessionToken: string, id: number, file: File,
): Promise<{ document_id: number; job_id: number; status: string }> {
  const form = new FormData();
  form.append("file", file);
  return request(`/api/builder/agents/${id}/documents`, {
    method: "POST",
    headers: authHeaders(sessionToken),
    body: form,
  });
}

export function deleteMyAgent(sessionToken: string, id: number): Promise<{ deleted: boolean; agent_id: number }> {
  return request(`/api/builder/agents/${id}`, { method: "DELETE", headers: authHeaders(sessionToken) });
}

// --- Tools ---

export function listToolCatalog(sessionToken: string): Promise<Tool[]> {
  return request("/api/builder/tools", { headers: authHeaders(sessionToken) });
}

export function getMyAgentTools(sessionToken: string, agentId: number): Promise<AgentTool[]> {
  return request(`/api/builder/agents/${agentId}/tools`, { headers: authHeaders(sessionToken) });
}

export function updateMyAgentTools(
  sessionToken: string, agentId: number, toolKeys: string[],
): Promise<AgentTool[]> {
  return request(`/api/builder/agents/${agentId}/tools`, {
    method: "PUT",
    headers: authHeaders(sessionToken),
    body: JSON.stringify({ tool_keys: toolKeys }),
  });
}

export function getMyAgentToolExecutions(
  sessionToken: string, agentId: number, limit = 50,
): Promise<ToolExecutionLog[]> {
  return request(`/api/builder/agents/${agentId}/tool-executions?limit=${limit}`, {
    headers: authHeaders(sessionToken),
  });
}

// --- Sessions, customers, leads (scoped to my own agents) ---

export function listMySessions(sessionToken: string, agentId?: number): Promise<BuilderSessionRow[]> {
  const qs = agentId ? `?agent_id=${agentId}` : "";
  return request(`/api/builder/sessions${qs}`, { headers: authHeaders(sessionToken) });
}

export function listMyCustomers(sessionToken: string): Promise<BuilderCustomerRow[]> {
  return request("/api/builder/customers", { headers: authHeaders(sessionToken) });
}

export function listMyLeads(
  sessionToken: string, filters?: { agent_id?: number; status?: string },
): Promise<Lead[]> {
  const params = new URLSearchParams();
  if (filters?.agent_id) params.set("agent_id", String(filters.agent_id));
  if (filters?.status) params.set("status", filters.status);
  const qs = params.toString();
  return request(`/api/builder/leads${qs ? `?${qs}` : ""}`, { headers: authHeaders(sessionToken) });
}

export function getMyLeadStats(sessionToken: string, agentId?: number): Promise<LeadStats> {
  const qs = agentId ? `?agent_id=${agentId}` : "";
  return request(`/api/builder/leads/stats${qs}`, { headers: authHeaders(sessionToken) });
}

export function getMyLead(sessionToken: string, id: number): Promise<Lead> {
  return request(`/api/builder/leads/${id}`, { headers: authHeaders(sessionToken) });
}

export function updateMyLead(
  sessionToken: string, id: number, payload: { status?: string; notes?: string },
): Promise<Lead> {
  return request(`/api/builder/leads/${id}`, {
    method: "PATCH",
    headers: authHeaders(sessionToken),
    body: JSON.stringify(payload),
  });
}

export function getMyLeadConversation(
  sessionToken: string, id: number,
): Promise<{ messages: import("../types").ChatMessage[] }> {
  return request(`/api/builder/leads/${id}/conversation`, { headers: authHeaders(sessionToken) });
}
