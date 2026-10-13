"""Markdown loader. The implementation lives in text.py (MarkdownLoader
just treats markdown as plain text for chunking purposes); this module
exists so the file layout matches the other one-loader-per-format modules
and `from app.rag.ingestion.loaders.markdown import MarkdownLoader` works
as expected."""
from __future__ import annotations

from app.rag.ingestion.loaders.text import MarkdownLoader

__all__ = ["MarkdownLoader"]
