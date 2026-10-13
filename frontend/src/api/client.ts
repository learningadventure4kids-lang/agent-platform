import type {
  Agent, AgentCreated, AgentTool, ChatMessage, Lead, LeadStats, TokenRotated, Tool, ToolExecutionLog,
} from "../types";
import { ApiError, request } from "./http";

export { ApiError };

// A customer-session credential is carried through every one of these
// functions as the exact same opaque "adminKey" string the platform
// operator's X-Admin-Key already was -- see hooks/useAdminAuth.ts, which
// is the only place that decides which kind of login is active and
// prefixes a customer's session token with CUSTOMER_CREDENTIAL_PREFIX.
// That keeps this as the single place that has to know the encoding, so
// none of the ~40 call sites across the admin pages had to change.
const CUSTOMER_CREDENTIAL_PREFIX = "cust:";

function authHeaders(adminKey: string): HeadersInit {
  if (adminKey.startsWith(CUSTOMER_CREDENTIAL_PREFIX)) {
    return { Authorization: `Bearer ${adminKey.slice(CUSTOMER_CREDENTIAL_PREFIX.length)}` };
  }
  return { "X-Admin-Key": adminKey };
}

export function adminLogin(username: string, password: string): Promise<{ admin_key: string }> {
  return request("/api/admin/login", { method: "POST", body: JSON.stringify({ username, password }) });
}

// --- Agents ---

export function listAgents(adminKey: string): Promise<Agent[]> {
  return request("/api/admin/agents", { headers: authHeaders(adminKey) });
}

export function getAgent(adminKey: string, id: number): Promise<Agent> {
  return request(`/api/admin/agents/${id}`, { headers: authHeaders(adminKey) });
}

export function createAgent(adminKey: string, payload: Record<string, unknown>): Promise<AgentCreated> {
  return request("/api/admin/agents", {
    method: "POST",
    headers: authHeaders(adminKey),
    body: JSON.stringify(payload),
  });
}

export function updateAgent(adminKey: string, id: number, payload: Partial<Agent>): Promise<Agent> {
  return request(`/api/admin/agents/${id}`, {
    method: "PUT",
    headers: authHeaders(adminKey),
    body: JSON.stringify(payload),
  });
}

export function deleteAgent(adminKey: string, id: number): Promise<void> {
  return request(`/api/admin/agents/${id}`, { method: "DELETE", headers: authHeaders(adminKey) });
}

export function rotateToken(adminKey: string, id: number): Promise<TokenRotated> {
  return request(`/api/admin/agents/${id}/rotate-token`, { method: "POST", headers: authHeaders(adminKey) });
}

export function setAgentEnabled(adminKey: string, id: number, enabled: boolean): Promise<Agent> {
  return request(`/api/admin/agents/${id}/${enabled ? "enable" : "disable"}`, {
    method: "POST",
    headers: authHeaders(adminKey),
  });
}

// --- Tools ---

export function listTools(adminKey: string): Promise<Tool[]> {
  return request("/api/admin/tools", { headers: authHeaders(adminKey) });
}

export function getAgentTools(adminKey: string, agentId: number): Promise<AgentTool[]> {
  return request(`/api/admin/agents/${agentId}/tools`, { headers: authHeaders(adminKey) });
}

export function getAgentToolExecutions(
  adminKey: string, agentId: number, limit = 100,
): Promise<ToolExecutionLog[]> {
  return request(`/api/admin/agents/${agentId}/tool-executions?limit=${limit}`, {
    headers: authHeaders(adminKey),
  });
}

export function updateAgentTools(adminKey: string, agentId: number, toolKeys: string[]): Promise<AgentTool[]> {
  return request(`/api/admin/agents/${agentId}/tools`, {
    method: "PUT",
    headers: authHeaders(adminKey),
    body: JSON.stringify({ tool_keys: toolKeys }),
  });
}

// --- Leads ---

export function listLeads(adminKey: string, filters?: { agent_id?: number; status?: string }): Promise<Lead[]> {
  const params = new URLSearchParams();
  if (filters?.agent_id) params.set("agent_id", String(filters.agent_id));
  if (filters?.status) params.set("status", filters.status);
  const qs = params.toString();
  return request(`/api/admin/leads${qs ? `?${qs}` : ""}`, { headers: authHeaders(adminKey) });
}

export function getLeadStats(adminKey: string, agentId?: number): Promise<LeadStats> {
  const qs = agentId ? `?agent_id=${agentId}` : "";
  return request(`/api/admin/leads/stats${qs}`, { headers: authHeaders(adminKey) });
}

export function getLead(adminKey: string, id: number): Promise<Lead> {
  return request(`/api/admin/leads/${id}`, { headers: authHeaders(adminKey) });
}

export function updateLead(adminKey: string, id: number, payload: { status?: string; notes?: string }): Promise<Lead> {
  return request(`/api/admin/leads/${id}`, {
    method: "PATCH",
    headers: authHeaders(adminKey),
    body: JSON.stringify(payload),
  });
}

export function getLeadConversation(adminKey: string, id: number): Promise<{ messages: ChatMessage[] }> {
  return request(`/api/admin/leads/${id}/conversation`, { headers: authHeaders(adminKey) });
}

// --- Sessions & Customers ---

export interface SessionRow {
  session_id: string;
  agent_key: string | null;
  agent_brand: string | null;
  customer_name: string | null;
  customer_contact: string | null;
  conversation_status: string;
  message_count: number;
  created_at: string;
  last_activity_at: string;
}

export function listSessions(adminKey: string, agentId?: number): Promise<SessionRow[]> {
  const qs = agentId ? `?agent_id=${agentId}` : "";
  return request(`/api/admin/sessions${qs}`, { headers: authHeaders(adminKey) });
}

export interface CustomerRow {
  id: number;
  name: string | null;
  email: string | null;
  phone: string | null;
  session_count: number;
  lead_count: number;
  created_at: string;
}

export function listCustomers(adminKey: string): Promise<CustomerRow[]> {
  return request("/api/admin/customers", { headers: authHeaders(adminKey) });
}

// --- Knowledge base ---

export interface KnowledgeDocument {
  id: number;
  agent_id: number;
  original_filename: string;
  file_type: string;
  file_size: number;
  status: "PENDING" | "PROCESSING" | "READY" | "FAILED";
  processing_error: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeJobStatus {
  id: number;
  document_id: number;
  job_type: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  progress: number;
  error_message: string | null;
}

export function listDocuments(adminKey: string, agentId: number): Promise<KnowledgeDocument[]> {
  return request(`/api/knowledge?agent_id=${agentId}`, { headers: authHeaders(adminKey) });
}

export function uploadDocument(
  adminKey: string,
  agentId: number,
  file: File
): Promise<{ document_id: number; job_id: number; status: string }> {
  const form = new FormData();
  form.append("agent_id", String(agentId));
  form.append("file", file);
  // `request()` detects a FormData body and skips the JSON Content-Type
  // default automatically, letting the browser set its own multipart
  // boundary header -- see api/http.ts.
  return request("/api/knowledge/upload", { method: "POST", headers: authHeaders(adminKey), body: form });
}

export function deleteDocument(adminKey: string, documentId: number): Promise<void> {
  return request(`/api/knowledge/${documentId}`, { method: "DELETE", headers: authHeaders(adminKey) });
}

export function reprocessDocument(
  adminKey: string,
  documentId: number
): Promise<{ document_id: number; job_id: number; status: string }> {
  return request(`/api/knowledge/${documentId}/reprocess`, {
    method: "POST",
    headers: authHeaders(adminKey),
  });
}

export function getKnowledgeJob(adminKey: string, jobId: number): Promise<KnowledgeJobStatus> {
  return request(`/api/knowledge/jobs/${jobId}`, { headers: authHeaders(adminKey) });
}

// --- AI Providers ---

export interface AIProvider {
  id: number;
  provider_type: string;
  display_name: string;
  enabled: boolean;
  is_default: boolean;
  base_url: string | null;
  api_key_configured: boolean;
  model_name: string;
  temperature: number;
  max_tokens: number | null;
  timeout: number | null;
  supports_tools: boolean | null;
  supports_streaming: boolean | null;
  supports_vision: boolean | null;
  supports_structured_output: boolean | null;
  supports_embeddings: boolean | null;
  supports_reasoning: boolean | null;
  configuration_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  agent_count: number;
}

export interface ProviderTestResult {
  success: boolean;
  provider: string;
  model?: string | null;
  latency_ms?: number | null;
  error_code?: string | null;
  message?: string | null;
}

export function listProviderTypes(adminKey: string): Promise<{ implemented: string[]; all: string[] }> {
  return request("/api/admin/providers/types", { headers: authHeaders(adminKey) });
}

export function listProviders(adminKey: string): Promise<AIProvider[]> {
  return request("/api/admin/providers", { headers: authHeaders(adminKey) });
}

export function getProvider(adminKey: string, id: number): Promise<AIProvider> {
  return request(`/api/admin/providers/${id}`, { headers: authHeaders(adminKey) });
}

export function createProvider(adminKey: string, payload: Record<string, unknown>): Promise<AIProvider> {
  return request("/api/admin/providers", {
    method: "POST",
    headers: authHeaders(adminKey),
    body: JSON.stringify(payload),
  });
}

export function updateProvider(adminKey: string, id: number, payload: Record<string, unknown>): Promise<AIProvider> {
  return request(`/api/admin/providers/${id}`, {
    method: "PUT",
    headers: authHeaders(adminKey),
    body: JSON.stringify(payload),
  });
}

export function deleteProvider(adminKey: string, id: number): Promise<void> {
  return request(`/api/admin/providers/${id}`, { method: "DELETE", headers: authHeaders(adminKey) });
}

export function setDefaultProvider(adminKey: string, id: number): Promise<AIProvider> {
  return request(`/api/admin/providers/${id}/set-default`, { method: "POST", headers: authHeaders(adminKey) });
}

export function testProvider(adminKey: string, id: number): Promise<ProviderTestResult> {
  return request(`/api/admin/providers/${id}/test`, { method: "POST", headers: authHeaders(adminKey) });
}

export function discoverModels(adminKey: string, id: number): Promise<{ supported: boolean; models: string[] }> {
  return request(`/api/admin/providers/${id}/models`, { headers: authHeaders(adminKey) });
}
