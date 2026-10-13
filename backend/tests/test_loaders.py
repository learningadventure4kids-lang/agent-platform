import json

import pytest

from app.rag.ingestion.loaders import LoaderError, get_loader
from app.rag.ingestion.loaders.csv import CSVLoader
from app.rag.ingestion.loaders.json import JSONLoader
from app.rag.ingestion.loaders.markdown import MarkdownLoader
from app.rag.ingestion.loaders.text import TextLoader


def test_text_loader(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("Hello, this is a plain text file.")
    pages = TextLoader().load(str(p))
    assert len(pages) == 1
    assert "Hello" in pages[0].text


def test_text_loader_empty_file_raises(tmp_path):
    p = tmp_path / "empty.txt"
    p.write_text("   ")
    with pytest.raises(LoaderError):
        TextLoader().load(str(p))


def test_markdown_loader_treats_as_text(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# Heading\n\nSome **bold** content.")
    pages = MarkdownLoader().load(str(p))
    assert "Heading" in pages[0].text


def test_csv_loader_renders_rows(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("name,price\nRing,100\nNecklace,200\n")
    pages = CSVLoader().load(str(p))
    joined = "\n".join(pg.text for pg in pages)
    assert "name: Ring" in joined
    assert "price: 100" in joined


def test_csv_loader_no_rows_raises(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("name,price\n")
    with pytest.raises(LoaderError):
        CSVLoader().load(str(p))


def test_json_loader_list_of_faqs(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps([{"question": "Returns?", "answer": "30 days"}, {"question": "Ship?", "answer": "3-5 days"}]))
    pages = JSONLoader().load(str(p))
    assert len(pages) == 2
    assert "question: Returns?" in pages[0].text
    assert "answer: 30 days" in pages[0].text


def test_json_loader_single_object(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"policy": "return within 30 days"}))
    pages = JSONLoader().load(str(p))
    assert len(pages) == 1
    assert "policy: return within 30 days" in pages[0].text


def test_json_loader_invalid_json_raises(tmp_path):
    p = tmp_path / "a.json"
    p.write_text("{not valid json")
    with pytest.raises(LoaderError):
        JSONLoader().load(str(p))


def test_get_loader_unsupported_type_raises():
    with pytest.raises(LoaderError):
        get_loader("exe")


def test_get_loader_returns_correct_type():
    assert isinstance(get_loader("txt"), TextLoader)
    assert isinstance(get_loader("csv"), CSVLoader)
