"""Configurable text chunking. chunk_size/chunk_overlap come from
environment variables (app/config.py) rather than being hard-coded, per
the project brief -- callers can still override them explicitly (e.g. a
future per-agent chunking preference) without touching this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.config import get_settings


@dataclass
class TextPage:
    """One unit of source text with a known origin (e.g. one PDF page, or
    the whole file for formats without natural pages)."""

    text: str
    page: Optional[int] = None
    extra_metadata: dict = field(default_factory=dict)


@dataclass
class Chunk:
    content: str
    chunk_index: int
    metadata: dict


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Simple, dependency-free recursive-ish splitter: try to break on
    paragraph/sentence/word boundaries before falling back to a hard cut,
    always advancing by at least (chunk_size - chunk_overlap) characters so
    it can never loop forever on pathological input."""
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    separators = ["\n\n", "\n", ". ", " "]
    chunks: list[str] = []
    start = 0
    step = max(chunk_size - chunk_overlap, 1)

    while start < len(text):
        end = min(start + chunk_size, len(text))
        piece = text[start:end]

        if end < len(text):
            split_at = -1
            for sep in separators:
                idx = piece.rfind(sep)
                if idx > chunk_size * 0.4:  # don't cut too early in the window
                    split_at = idx + len(sep)
                    break
            if split_at != -1:
                piece = piece[:split_at]
                end = start + split_at

        piece = piece.strip()
        if piece:
            chunks.append(piece)

        if end >= len(text):
            break
        start = max(end - chunk_overlap, start + step)

    return chunks


def split_pages(
    pages: list[TextPage],
    chunk_size: Optional[int] = None,
    chunk_overlap: Optional[int] = None,
) -> list[Chunk]:
    """Splits a list of pages (already-extracted text) into overlapping
    chunks, preserving page numbers and any extra metadata in each chunk's
    metadata dict."""
    settings = get_settings()
    chunk_size = chunk_size or settings.CHUNK_SIZE
    chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    chunks: list[Chunk] = []
    index = 0
    for page in pages:
        for piece in _split_text(page.text, chunk_size, chunk_overlap):
            metadata = {**page.extra_metadata}
            if page.page is not None:
                metadata["page"] = page.page
            chunks.append(Chunk(content=piece, chunk_index=index, metadata=metadata))
            index += 1
    return chunks
