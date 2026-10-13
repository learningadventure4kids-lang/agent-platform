from __future__ import annotations

import csv

from app.rag.chunking.splitter import TextPage
from app.rag.ingestion.loaders.base import DocumentLoader, LoaderError


class CSVLoader(DocumentLoader):
    """Renders each row as `column: value` lines so the splitter's
    paragraph-boundary logic naturally keeps whole rows together where
    possible, and groups a batch of rows per "page" for reasonable chunk
    sizes on large files."""

    rows_per_page = 50

    def load(self, path: str) -> list[TextPage]:
        try:
            with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except OSError as exc:
            raise LoaderError(f"Could not read CSV: {exc}") from exc
        except csv.Error as exc:
            raise LoaderError(f"Could not parse CSV: {exc}") from exc

        if not rows:
            raise LoaderError("CSV file has no data rows.")

        pages: list[TextPage] = []
        for i in range(0, len(rows), self.rows_per_page):
            batch = rows[i : i + self.rows_per_page]
            blocks = []
            for row in batch:
                blocks.append("\n".join(f"{k}: {v}" for k, v in row.items() if v))
            pages.append(TextPage(text="\n\n".join(blocks), page=(i // self.rows_per_page) + 1))
        return pages
