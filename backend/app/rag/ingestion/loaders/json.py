from __future__ import annotations

import json

from app.rag.chunking.splitter import TextPage
from app.rag.ingestion.loaders.base import DocumentLoader, LoaderError


class JSONLoader(DocumentLoader):
    """Flattens arbitrary JSON into readable text. A top-level list is
    treated as one "page" per item (useful for FAQ-style
    `[{"question": ..., "answer": ...}, ...]` files); anything else
    becomes a single page."""

    def load(self, path: str) -> list[TextPage]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except OSError as exc:
            raise LoaderError(f"Could not read JSON: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LoaderError(f"Could not parse JSON: {exc}") from exc

        if isinstance(data, list) and data:
            pages = [
                TextPage(text=self._flatten(item), page=i + 1) for i, item in enumerate(data)
            ]
        else:
            pages = [TextPage(text=self._flatten(data), page=None)]

        if not any(p.text.strip() for p in pages):
            raise LoaderError("JSON file produced no text content.")
        return pages

    def _flatten(self, value, prefix: str = "") -> str:
        lines = []
        if isinstance(value, dict):
            for k, v in value.items():
                key = f"{prefix}{k}"
                if isinstance(v, (dict, list)):
                    lines.append(self._flatten(v, prefix=f"{key}."))
                else:
                    lines.append(f"{key}: {v}")
        elif isinstance(value, list):
            for i, v in enumerate(value):
                lines.append(self._flatten(v, prefix=f"{prefix}{i}."))
        else:
            lines.append(f"{prefix.rstrip('.')}: {value}")
        return "\n".join(lines)
