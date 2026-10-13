"""Loader abstraction: every supported file type implements `load(path)`
and returns a list of `TextPage`s (see app/rag/chunking/splitter.py) so the
rest of the ingestion pipeline never needs to know the file format.
Adding a new format is just adding a new loader here and registering it in
`LOADER_REGISTRY` -- no other ingestion code changes."""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.rag.chunking.splitter import TextPage


class DocumentLoader(ABC):
    @abstractmethod
    def load(self, path: str) -> list[TextPage]:
        ...


class LoaderError(Exception):
    """Raised when a file can't be parsed -- caught by the ingestion
    service and turned into a FAILED document/job with a friendly
    `processing_error`, never an unhandled exception."""
