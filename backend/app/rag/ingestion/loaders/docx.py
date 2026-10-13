from __future__ import annotations

from app.rag.chunking.splitter import TextPage
from app.rag.ingestion.loaders.base import DocumentLoader, LoaderError


class DOCXLoader(DocumentLoader):
    def load(self, path: str) -> list[TextPage]:
        try:
            import docx
        except ImportError as exc:  # pragma: no cover
            raise LoaderError("DOCX support requires the 'python-docx' package") from exc

        try:
            doc = docx.Document(path)
        except Exception as exc:
            raise LoaderError(f"Could not open DOCX: {exc}") from exc

        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        if not text.strip():
            raise LoaderError("No extractable text found in DOCX.")
        return [TextPage(text=text, page=None)]
