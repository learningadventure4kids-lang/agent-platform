"""Generic conversation state. Deliberately business-agnostic -- there is
no astrology- or jewellery-specific field here. Anything domain-specific
lives in tool arguments/results, not in this TypedDict, which is what lets
the same graph run every agent."""
from __future__ import annotations

from typing import Annotated, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    agent_id: int
    session_id: str
    messages: Annotated[list[BaseMessage], add_messages]

    customer_id: Optional[int]
    collected_fields: dict  # best-effort mirror of what's been said (name/email/phone if known)
    pending_lead: bool  # a lead-creation tool was attempted but not confirmed
    lead_created: bool
    tool_results: list[dict]
    conversation_status: str

    # --- LangGraph orchestration-layer fields (operational only -- never
    # chain-of-thought; see app/agents/graph.py for how these are used) ---
    current_action: Optional[str]  # tool_key the model most recently requested
    pending_actions: list[dict]  # normalized PlannedActions from validate_action, this round
    validated_actions: list[dict]  # the subset of pending_actions permission_check allowed
    denied_actions: list[dict]  # actions the permission_check node refused, and why (accumulates)
    handoff_requested: bool
    handoff_reason: Optional[str]
    provider_name: Optional[str]
    model_name: Optional[str]
