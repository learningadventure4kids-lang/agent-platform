from __future__ import annotations

from app.rag.chunking.splitter import TextPage
from app.rag.ingestion.loaders.base import DocumentLoader, LoaderError

try:
    from openpyxl import load_workbook
except ImportError:  # pragma: no cover - exercised only if the dep is missing
    load_workbook = None


class XLSXLoader(DocumentLoader):
    """Renders each row as `column: value` lines, same convention as
    CSVLoader, so a spreadsheet and a CSV export of it chunk the same
    way. One "page" per sheet (workbooks commonly have several), with
    rows batched within a sheet for reasonable chunk sizes on large
    sheets."""

    rows_per_page = 50

    def load(self, path: str) -> list[TextPage]:
        if load_workbook is None:  # pragma: no cover
            raise LoaderError("XLSX support requires the 'openpyxl' package.")

        try:
            workbook = load_workbook(filename=path, read_only=True, data_only=True)
        except Exception as exc:  # openpyxl raises several different types on bad files
            raise LoaderError(f"Could not read spreadsheet: {exc}") from exc

        pages: list[TextPage] = []
        page_num = 0

        for sheet in workbook.worksheets:
            rows = list(sheet.iter_rows(values_only=True))
            if not rows:
                continue
            header = [str(h) if h is not None else "" for h in rows[0]]
            data_rows = rows[1:]
            if not data_rows:
                continue

            for i in range(0, len(data_rows), self.rows_per_page):
                batch = data_rows[i : i + self.rows_per_page]
                blocks = []
                for row in batch:
                    pairs = [
                        f"{header[idx] or f'column_{idx + 1}'}: {value}"
                        for idx, value in enumerate(row)
                        if value is not None and value != ""
                    ]
                    if pairs:
                        blocks.append("\n".join(pairs))
                if not blocks:
                    continue
                page_num += 1
                text = f"Sheet: {sheet.title}\n\n" + "\n\n".join(blocks)
                pages.append(TextPage(text=text, page=page_num))

        if not pages:
            raise LoaderError("Spreadsheet has no data rows.")
        return pages
