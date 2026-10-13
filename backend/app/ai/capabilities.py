"""Declares what a given provider/model combination can actually do.
Checked before the agent graph relies on an optional capability (tool
calling being the main one today), so an unsupported combination fails
with a clean configuration error instead of a confusing runtime exception
from deep inside LangChain."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_tools: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_structured_output: bool = True
    supports_embeddings: bool = False
    supports_reasoning: bool = False
