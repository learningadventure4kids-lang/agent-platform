"""Normalizes "what should happen next" into a provider-independent shape
before it ever reaches LangGraph's permission/execution nodes.

Every provider this platform supports today (Ollama via qwen3, Groq/OpenAI/
OpenRouter/Azure via the OpenAI-compatible provider) exposes native
tool/function calling through LangChain's `bind_tools()`, so
`NativeToolCallPlanner` is the only concrete implementation that exists
right now. It is still worth having the `ActionPlanner` abstraction,
because the graph nodes (`agent_decision`, `validate_action`, ...) call
`get_action_planner(...)` and never touch `bind_tools` directly -- so a
future provider that *doesn't* support native tool calling (and instead
needs a JSON-in-the-content-string convention, or a constrained
structured-output call) can be added as a second `ActionPlanner`
implementation without changing a single line of graph.py. That is the
"seam" the project brief asks for: capability-driven selection of a
planner, with the graph itself staying generic.

`extract_actions()` returns `PlannedAction`s -- the normalized
`{"action": ..., "arguments": {...}}` shape from the spec -- built from
whatever the planner's `decide()` produced. The graph only ever acts on
`PlannedAction`s, never on raw provider output, which is what keeps native
tool calling from ever bypassing LangGraph's own permission validation:
the LLM's tool_calls are read here, turned into plain data, and from that
point on are just an action request like any other, subject to the same
`validate_action` / `permission_check` nodes regardless of which provider
produced them.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import StructuredTool

from app.ai.capabilities import ProviderCapabilities


@dataclass
class PlannedAction:
    """The normalized internal action format from the spec: a tool_key the
    model wants to call, plus the arguments it wants to call it with. Never
    trusted as authorization -- see app/agents/graph.py's permission_check
    node -- just a structured request."""

    tool_call_id: str
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


class ActionPlanner(ABC):
    """Turns the current conversation into either a final response or one
    or more `PlannedAction`s. Implementations may use whatever mechanism
    the provider supports (native tool calling, structured output, a JSON
    convention) -- the graph only ever sees the normalized result."""

    @abstractmethod
    def decide(self, system_prompt: str, messages: list[BaseMessage]) -> AIMessage:
        """Invoke the underlying model and return its raw response message.
        Kept separate from `extract_actions` so the graph can still read
        `.content` for a plain-text reply when no action is requested."""

    @abstractmethod
    def extract_actions(self, response: AIMessage) -> list[PlannedAction]:
        """Normalize whatever the model produced into `PlannedAction`s.
        Returns an empty list when the model didn't request any action."""


class NativeToolCallPlanner(ActionPlanner):
    """Wraps a LangChain chat model's `bind_tools()` / `.tool_calls`. This
    is the concrete planner used by every provider this platform ships
    today (Ollama, OpenAI-compatible/Groq/OpenRouter/Azure) -- all of them
    report `supports_tools=True` and LangChain normalizes their native
    function-calling APIs to the same `AIMessage.tool_calls` shape, so one
    implementation covers all of them."""

    def __init__(self, chat_model, tools: list[StructuredTool]):
        self._bound_model = chat_model.bind_tools(tools) if tools else chat_model

    def decide(self, system_prompt: str, messages: list[BaseMessage]) -> AIMessage:
        return self._bound_model.invoke([SystemMessage(system_prompt)] + messages)

    def extract_actions(self, response: AIMessage) -> list[PlannedAction]:
        calls = getattr(response, "tool_calls", None) or []
        return [
            PlannedAction(tool_call_id=call["id"], tool_name=call["name"], arguments=call.get("args") or {})
            for call in calls
        ]


def get_action_planner(
    chat_model, tools: list[StructuredTool], capabilities: ProviderCapabilities
) -> ActionPlanner:
    """The one seam a future non-tool-calling provider would plug into:
    branch on `capabilities.supports_tools` (and, later, on other capability
    flags such as `supports_structured_output`) to pick a different
    `ActionPlanner` implementation. Every provider this platform supports
    today has `supports_tools=True`, so this always returns
    `NativeToolCallPlanner` in practice -- the branch exists so adding the
    next provider type doesn't require touching app/agents/graph.py."""
    # NOTE: when a provider without native tool calling is added, branch
    # here on `capabilities.supports_tools` and return e.g. a
    # `StructuredOutputPlanner`/`JSONActionPlanner` instead. The graph
    # nodes below only ever call `ActionPlanner.decide`/`.extract_actions`,
    # so no other file needs to change.
    return NativeToolCallPlanner(chat_model, tools)
