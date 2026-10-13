"""The single source of truth for what tools exist and what each one does.

`TOOL_REGISTRY` is keyed by tool_key (the same key stored in the `tools`
table and referenced by `agent_tools`). Each entry carries display metadata
(for the admin dashboard) plus which "module" builds it -- modules build
several related tools at once (e.g. all three jewellery tools share one
ToolContext), but each individual tool_key can still be independently
enabled/disabled per agent.

As of the LangGraph-orchestration upgrade, each entry also carries
*operational* metadata that the graph itself (not just the admin UI) reads
at execution time:

- category: groups tools for the admin dashboard and for audit reporting.
- requires_confirmation: enforced generically by the graph's
  `permission_check` node (see app/agents/graph.py) -- if true, a tool call
  is denied before it ever reaches the tool function unless its arguments
  include `confirmed: true`. This is a second, structural line of defense
  on top of whatever a tool's own function body checks; it does not depend
  on any single tool remembering to validate it.
- risk_level: informational today (surfaced in the admin dashboard /
  audit log), reserved for future stricter policies (e.g. requiring admin
  approval for "high" risk tools).
- timeout_seconds: enforced by the graph's `execute_tool` node -- a tool
  that runs longer than this is aborted and recorded as a timeout rather
  than left to hang the whole chat turn.

`build_tools_for_agent` is the only function the agent graph calls: it
builds *only* the tools the given agent is permitted to use. This is the
structural enforcement behind "an agent must never execute a tool outside
its permissions" -- there is simply no code path that binds an unpermitted
tool to the LLM in the first place.
"""
from __future__ import annotations

from typing import TypedDict

from langchain_core.tools import StructuredTool

from app.tools.astrology import build_astrology_tools
from app.tools.common import ToolContext, build_common_tools
from app.tools.jewellery import build_jewellery_tools
from app.tools.knowledge import build_knowledge_tools
from app.tools.realestate import build_realestate_tools


class ToolMetadata(TypedDict):
    name: str
    description: str
    category: str
    requires_confirmation: bool
    risk_level: str
    timeout_seconds: float


# tool_key -> metadata, for seeding the `tools` table / admin dashboard AND
# for the graph's generic permission/timeout enforcement. The *behavior*
# lives in the builder modules above -- this is deliberately just data.
TOOL_REGISTRY: dict[str, ToolMetadata] = {
    "create_lead": {
        "name": "Create Lead",
        "description": "Generic lead capture, available to any agent.",
        "category": "lead_generation",
        "requires_confirmation": True,
        "risk_level": "medium",
        "timeout_seconds": 10,
    },
    "get_known_info": {
        "name": "Recall Visitor Info",
        "description": "Lets the assistant check what's already known before re-asking.",
        "category": "utility",
        "requires_confirmation": False,
        "risk_level": "low",
        "timeout_seconds": 5,
    },
    "validate_contact_info": {
        "name": "Validate Contact Info",
        "description": "Validates email/phone format before confirming with the visitor.",
        "category": "utility",
        "requires_confirmation": False,
        "risk_level": "low",
        "timeout_seconds": 5,
    },
    "request_human_handoff": {
        "name": "Request Human Handoff",
        "description": "Flags the conversation for a human team member to take over.",
        "category": "handoff",
        "requires_confirmation": False,
        "risk_level": "low",
        "timeout_seconds": 10,
    },
    "search_jewellery": {
        "name": "Search Jewellery",
        "description": "Search the jewellery product catalog.",
        "category": "catalog",
        "requires_confirmation": False,
        "risk_level": "low",
        "timeout_seconds": 8,
    },
    "get_product_details": {
        "name": "Product Details",
        "description": "Look up full details for a specific product.",
        "category": "catalog",
        "requires_confirmation": False,
        "risk_level": "low",
        "timeout_seconds": 8,
    },
    "create_jewellery_lead": {
        "name": "Create Jewellery Lead",
        "description": "Capture a jewellery consultation lead with product/budget/occasion.",
        "category": "lead_generation",
        "requires_confirmation": True,
        "risk_level": "medium",
        "timeout_seconds": 10,
    },
    "calculate_birth_chart": {
        "name": "Calculate Birth Chart",
        "description": "Astrology chart calculation (demo ephemeris data).",
        "category": "calculation",
        "requires_confirmation": False,
        "risk_level": "low",
        "timeout_seconds": 8,
    },
    "create_astrology_consultation": {
        "name": "Create Astrology Consultation",
        "description": "Capture an astrology consultation request.",
        "category": "lead_generation",
        "requires_confirmation": True,
        "risk_level": "medium",
        "timeout_seconds": 10,
    },
    "search_properties": {
        "name": "Search Properties",
        "description": "Search the property listing catalog.",
        "category": "catalog",
        "requires_confirmation": False,
        "risk_level": "low",
        "timeout_seconds": 8,
    },
    "get_property_details": {
        "name": "Property Details",
        "description": "Look up full details for a specific property listing.",
        "category": "catalog",
        "requires_confirmation": False,
        "risk_level": "low",
        "timeout_seconds": 8,
    },
    "search_knowledge_base": {
        "name": "Search Knowledge Base",
        "description": "Retrieve relevant chunks from this agent's uploaded documents (policies, FAQs, product info).",
        "category": "knowledge",
        "requires_confirmation": False,
        "risk_level": "low",
        "timeout_seconds": 15,
    },
}


def get_tool_metadata(tool_key: str) -> ToolMetadata | None:
    """Look up a tool's operational metadata. Returns None for an unknown
    key -- callers (graph permission/timeout logic) treat that the same as
    "deny": there is no metadata to say this tool is safe to run."""
    return TOOL_REGISTRY.get(tool_key)


def _all_available_tools(ctx: ToolContext) -> dict[str, StructuredTool]:
    """Every tool that *could* be built, keyed by tool_key. Building a tool
    is cheap (just closures) so we build the full set and then filter by
    permission, rather than trying to build only the allowed subset."""
    tools: dict[str, StructuredTool] = {}
    tools.update(build_common_tools(ctx, source=f"{ctx.agent.agent_key}-widget"))
    tools.update(build_jewellery_tools(ctx))
    tools.update(build_astrology_tools(ctx))
    tools.update(build_realestate_tools(ctx))
    tools.update(build_knowledge_tools(ctx))
    return tools


def build_tools_for_agent(ctx: ToolContext, allowed_tool_keys: list[str]) -> list[StructuredTool]:
    """The only entry point the agent graph should use. Returns only the
    tools in `allowed_tool_keys`, silently ignoring any key that doesn't
    correspond to a real, buildable tool."""
    available = _all_available_tools(ctx)
    return [available[key] for key in allowed_tool_keys if key in available]
