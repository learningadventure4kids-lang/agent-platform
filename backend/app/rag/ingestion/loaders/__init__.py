"""Maps a file extension to its loader. Adding a new supported format is:
write the loader module, import it here, add one line to LOADER_REGISTRY."""
from __future__ import annotations

from app.rag.ingestion.loaders.base import DocumentLoader, LoaderError
from app.rag.ingestion.loaders.csv import CSVLoader
from app.rag.ingestion.loaders.docx import DOCXLoader
from app.rag.ingestion.loaders.json import JSONLoader
from app.rag.ingestion.loaders.markdown import MarkdownLoader
from app.rag.ingestion.loaders.pdf import PDFLoader
from app.rag.ingestion.loaders.text import TextLoader
from app.rag.ingestion.loaders.xlsx import XLSXLoader

LOADER_REGISTRY: dict[str, type[DocumentLoader]] = {
    "pdf": PDFLoader,
    "docx": DOCXLoader,
    "txt": TextLoader,
    "csv": CSVLoader,
    "json": JSONLoader,
    "md": MarkdownLoader,
    "xlsx": XLSXLoader,
}


def get_loader(file_type: str) -> DocumentLoader:
    cls = LOADER_REGISTRY.get(file_type.lower())
    if not cls:
        raise LoaderError(f"Unsupported file type: {file_type}")
    return cls()


__all__ = ["LOADER_REGISTRY", "get_loader", "LoaderError", "DocumentLoader"]
