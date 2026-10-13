from __future__ import annotations

from app.rag.chunking.splitter import TextPage
from app.rag.ingestion.loaders.base import DocumentLoader, LoaderError


class PDFLoader(DocumentLoader):
    def load(self, path: str) -> list[TextPage]:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover
            raise LoaderError("PDF support requires the 'pypdf' package") from exc

        try:
            reader = PdfReader(path)
        except Exception as exc:
            raise LoaderError(f"Could not open PDF: {exc}") from exc

        pages: list[TextPage] = []
        for i, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                pages.append(TextPage(text=text, page=i))

        if not pages:
            raise LoaderError("No extractable text found in PDF (it may be a scanned image).")
        return pages
