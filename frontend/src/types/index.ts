export interface Agent {
  id: number;
  agent_key: string;
  name: string;
  brand_name: string;
  description: string | null;
  system_prompt: string;
  welcome_message: string;
  suggestions: string[];
  lead_fields: string[];
  theme: Record<string, unknown>;
  model: string;
  temperature: number;
  max_tokens: number | null;
  enabled: boolean;
  allowed_domains: string[];
  provider_id: number | null;
  fallback_provider_id: number | null;
  created_at: string;
  updated_at: string;
  tool_count: number;
  session_count: number;
  lead_count: number;
}

export interface AgentCreated extends Agent {
  public_token: string;
}

export interface TokenRotated {
  agent_id: number;
  public_token: string;
}

export interface Tool {
  id: number;
  tool_key: string;
  name: string;
  description: string | null;
  enabled: boolean;
  category: string | null;
  requires_confirmation: boolean | null;
  risk_level: string | null;
  timeout_seconds: number | null;
}

export interface AgentTool extends Tool {
  granted: boolean;
}

export interface ToolExecutionLog {
  id: number;
  agent_id: number;
  session_id: string;
  tool_name: string;
  status: "success" | "denied" | "error" | "timeout" | string;
  error_category: string | null;
  sanitized_arguments: Record<string, unknown>;
  sanitized_result: string | null;
  started_at: string;
  completed_at: string | null;
  duration_ms: number | null;
}

export interface Lead {
  id: number;
  agent_id: number;
  session_id: string | null;
  name: string | null;
  email: string | null;
  phone: string | null;
  source: string | null;
  status: string;
  score: number;
  metadata_json: Record<string, unknown>;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
}

export interface LeadStats {
  total: number;
  new: number;
  qualified: number;
  contacted: number;
  converted: number;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  created_at?: string;
}

// --- Self-serve builder ---

export interface CustomerUser {
  id: number;
  email: string;
  name: string;
  company_name: string | null;
  plan: "free" | "plus";
  created_at: string;
}

export interface PlanInfo {
  plan: "free" | "plus";
  max_documents_per_agent: number;
  max_file_size_mb: number;
}

export interface AuthResponse {
  session_token: string;
  user: CustomerUser;
}

export interface Persona {
  key: string;
  label: string;
  icon: string;
  blurb: string;
  specialized: boolean;
  welcome_message: string;
  suggestions: string[];
}

export interface BuilderAgent {
  id: number;
  agent_key: string;
  persona_key: string | null;
  name: string;
  brand_name: string;
  welcome_message: string;
  suggestions: string[];
  system_prompt: string;
  allowed_domains: string[];
  theme: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
  tool_count: number;
  session_count: number;
  lead_count: number;
}

export interface EmbedSnippet {
  agent_id: number;
  public_token: string;
  script_tag: string;
  install_snippet: string;
}

export interface BuilderDocument {
  id: number;
  original_filename: string;
  file_type: string;
  status: string;
  processing_error: string | null;
  chunk_count: number;
  created_at: string;
}

export interface BuilderSessionRow {
  session_id: string;
  agent_id: number;
  agent_key: string | null;
  agent_brand: string | null;
  customer_name: string | null;
  customer_contact: string | null;
  conversation_status: string;
  message_count: number;
  created_at: string;
  last_activity_at: string;
}

export interface BuilderCustomerRow {
  id: number;
  name: string | null;
  email: string | null;
  phone: string | null;
  session_count: number;
  lead_count: number;
  created_at: string;
}

export interface PreviewChatResponse {
  session_id: string;
  agent: {
    name: string;
    brand: string;
    welcome_message: string;
    suggestions: string[];
    theme: Record<string, unknown>;
  };
  response: string;
  message_id: number;
  lead_created: boolean;
}
