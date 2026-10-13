"""Pydantic schemas for the API layer. Kept separate from the SQLAlchemy
models in app/models/ so the API contract and the DB schema can evolve
independently."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Chat / session (public, token-authenticated) ---

class ChatRequest(BaseModel):
    agent_token: str
    session_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=4000)


class PreviewChatRequest(BaseModel):
    """Same shape as ChatRequest minus `agent_token` -- the builder's
    preview-chat route authenticates by session + ownership instead (see
    app/api/builder.py), so there is no public token involved at all."""
    session_id: Optional[str] = None
    message: str = Field(min_length=1, max_length=4000)


class AgentPublicInfo(BaseModel):
    name: str
    brand: str
    welcome_message: str
    suggestions: list[str] = []
    theme: dict = {}


class ChatResponse(BaseModel):
    session_id: str
    agent: AgentPublicInfo
    response: str
    message_id: int
    lead_created: bool = False


class MessageOut(BaseModel):
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class SessionStateOut(BaseModel):
    session_id: str
    agent: AgentPublicInfo
    conversation_status: str
    is_returning: bool = False
    messages: list[MessageOut] = []


class CreateSessionRequest(BaseModel):
    agent_token: str


# --- Admin: agents ---

class AgentCreate(BaseModel):
    agent_key: str
    tenant_id: Optional[str] = None  # defaults to agent_key if omitted
    name: str
    brand_name: str
    description: Optional[str] = None
    system_prompt: str
    welcome_message: str
    suggestions: list[str] = []
    lead_fields: list[str] = []
    theme: dict = {}
    model: str = "qwen3:8b"
    temperature: float = 0.4
    max_tokens: Optional[int] = None
    enabled: bool = True
    allowed_domains: list[str] = []
    tool_keys: list[str] = []
    provider_id: Optional[int] = None
    fallback_provider_id: Optional[int] = None


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    brand_name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    suggestions: Optional[list[str]] = None
    lead_fields: Optional[list[str]] = None
    theme: Optional[dict] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    enabled: Optional[bool] = None
    allowed_domains: Optional[list[str]] = None
    provider_id: Optional[int] = None
    fallback_provider_id: Optional[int] = None


class AgentOut(BaseModel):
    id: int
    agent_key: str
    tenant_id: str
    name: str
    brand_name: str
    description: Optional[str]
    system_prompt: str
    welcome_message: str
    suggestions: list[str]
    lead_fields: list[str]
    theme: dict
    model: str
    temperature: float
    max_tokens: Optional[int]
    enabled: bool
    allowed_domains: list[str]
    provider_id: Optional[int]
    fallback_provider_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    tool_count: int = 0
    session_count: int = 0
    lead_count: int = 0

    class Config:
        from_attributes = True


class AgentCreatedOut(AgentOut):
    public_token: str  # shown exactly once


class TokenRotatedOut(BaseModel):
    agent_id: int
    public_token: str  # shown exactly once


# --- Admin: tools ---

class ToolOut(BaseModel):
    id: int
    tool_key: str
    name: str
    description: Optional[str]
    enabled: bool
    category: Optional[str] = None
    requires_confirmation: Optional[bool] = None
    risk_level: Optional[str] = None
    timeout_seconds: Optional[float] = None

    class Config:
        from_attributes = True


class AgentToolOut(ToolOut):
    granted: bool


class ToolExecutionLogOut(BaseModel):
    id: int
    agent_id: int
    session_id: str
    tool_name: str
    status: str
    error_category: Optional[str] = None
    sanitized_arguments: dict
    sanitized_result: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None

    class Config:
        from_attributes = True


class AgentToolsUpdate(BaseModel):
    tool_keys: list[str]


# --- Admin: leads ---

class LeadOut(BaseModel):
    id: int
    agent_id: int
    session_id: Optional[str]
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    source: Optional[str]
    status: str
    score: int
    metadata_json: dict
    is_demo: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class LeadStatsOut(BaseModel):
    total: int
    new: int
    qualified: int
    contacted: int
    converted: int


# --- Admin auth ---

class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminLoginResponse(BaseModel):
    admin_key: str


# --- Admin: AI providers ---
# IMPORTANT: no schema in this section ever includes the raw or encrypted
# API key. Write requests accept a plaintext `api_key` (encrypted before
# storage, see app/api/admin_providers.py); every response schema only
# ever exposes `api_key_configured: bool`.

class AIProviderCreate(BaseModel):
    provider_type: str
    display_name: str
    enabled: bool = True
    is_default: bool = False
    base_url: Optional[str] = None
    api_key: Optional[str] = None  # plaintext in the request only; encrypted before storage
    model_name: str
    temperature: float = 0.4
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None
    supports_tools: Optional[bool] = None
    supports_streaming: Optional[bool] = None
    supports_vision: Optional[bool] = None
    supports_structured_output: Optional[bool] = None
    supports_embeddings: Optional[bool] = None
    supports_reasoning: Optional[bool] = None
    configuration_json: dict = {}


class AIProviderUpdate(BaseModel):
    display_name: Optional[str] = None
    enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None  # provide to rotate; omit to leave unchanged
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None
    supports_tools: Optional[bool] = None
    supports_streaming: Optional[bool] = None
    supports_vision: Optional[bool] = None
    supports_structured_output: Optional[bool] = None
    supports_embeddings: Optional[bool] = None
    supports_reasoning: Optional[bool] = None
    configuration_json: Optional[dict] = None


class AIProviderOut(BaseModel):
    id: int
    provider_type: str
    display_name: str
    enabled: bool
    is_default: bool
    base_url: Optional[str]
    api_key_configured: bool
    model_name: str
    temperature: float
    max_tokens: Optional[int]
    timeout: Optional[float]
    supports_tools: Optional[bool]
    supports_streaming: Optional[bool]
    supports_vision: Optional[bool]
    supports_structured_output: Optional[bool]
    supports_embeddings: Optional[bool]
    supports_reasoning: Optional[bool]
    configuration_json: dict
    created_at: datetime
    updated_at: datetime
    agent_count: int = 0


class ProviderTestResultOut(BaseModel):
    success: bool
    provider: str
    model: Optional[str] = None
    latency_ms: Optional[int] = None
    error_code: Optional[str] = None
    message: Optional[str] = None


# --- Self-serve builder: user accounts ---

class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=200)
    name: str = Field(min_length=1, max_length=120)
    company_name: Optional[str] = Field(default=None, max_length=160)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    company_name: Optional[str] = None
    plan: str
    created_at: datetime

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    session_token: str  # shown exactly once, at signup/login time
    user: UserOut


# --- Self-serve builder: personas ---

class PersonaOut(BaseModel):
    key: str
    label: str
    icon: str
    blurb: str
    specialized: bool
    welcome_message: str
    suggestions: list[str]


# --- Self-serve builder: agents ---

class BuilderAgentCreate(BaseModel):
    persona_key: str
    name: str = Field(min_length=1, max_length=80, description="Your assistant's name, e.g. 'Aria'")
    brand_name: str = Field(min_length=1, max_length=120, description="Your business name")
    welcome_message: Optional[str] = Field(default=None, max_length=2000)
    accent_color: Optional[str] = Field(default=None, max_length=20, description="e.g. '#7c5cff'")


class BuilderAgentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    brand_name: Optional[str] = Field(default=None, max_length=120)
    welcome_message: Optional[str] = Field(default=None, max_length=2000)
    system_prompt: Optional[str] = None
    suggestions: Optional[list[str]] = None
    allowed_domains: Optional[list[str]] = None
    accent_color: Optional[str] = Field(default=None, max_length=20)
    enabled: Optional[bool] = None


class BuilderAgentOut(BaseModel):
    id: int
    agent_key: str
    persona_key: Optional[str] = None
    name: str
    brand_name: str
    welcome_message: str
    suggestions: list[str]
    system_prompt: str
    allowed_domains: list[str] = []
    theme: dict
    enabled: bool
    created_at: datetime
    tool_count: int = 0
    session_count: int = 0
    lead_count: int = 0

    class Config:
        from_attributes = True


class EmbedSnippetOut(BaseModel):
    agent_id: int
    public_token: str  # shown exactly once, at creation/rotation time
    script_tag: str
    install_snippet: str
