from __future__ import annotations

from app.rag.chunking.splitter import TextPage
from app.rag.ingestion.loaders.base import DocumentLoader, LoaderError


class TextLoader(DocumentLoader):
    def load(self, path: str) -> list[TextPage]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as exc:
            raise LoaderError(f"Could not read file: {exc}") from exc

        if not text.strip():
            raise LoaderError("File is empty.")
        return [TextPage(text=text, page=None)]


class MarkdownLoader(TextLoader):
    """Markdown is treated as plain text for chunking purposes -- headings
    and structure still help the splitter find good break points via
    blank-line/paragraph boundaries without needing a full MD parser."""
