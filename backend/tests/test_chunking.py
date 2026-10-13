from app.rag.chunking.splitter import TextPage, split_pages


def test_short_text_becomes_one_chunk():
    chunks = split_pages([TextPage(text="Hello world.", page=1)], chunk_size=800, chunk_overlap=100)
    assert len(chunks) == 1
    assert chunks[0].content == "Hello world."
    assert chunks[0].metadata["page"] == 1


def test_long_text_is_split_into_multiple_chunks():
    text = "This is a sentence. " * 200  # 4000 chars
    chunks = split_pages([TextPage(text=text, page=1)], chunk_size=200, chunk_overlap=50)
    assert len(chunks) > 1
    assert all(len(c.content) <= 250 for c in chunks)  # some slack for boundary search


def test_chunks_have_sequential_index_across_pages():
    pages = [TextPage(text="First page content here.", page=1), TextPage(text="Second page content here.", page=2)]
    chunks = split_pages(pages, chunk_size=800, chunk_overlap=100)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert chunks[0].metadata["page"] == 1
    assert chunks[1].metadata["page"] == 2


def test_empty_text_produces_no_chunks():
    chunks = split_pages([TextPage(text="   ", page=1)])
    assert chunks == []


def test_extra_metadata_is_preserved():
    pages = [TextPage(text="Some content.", page=1, extra_metadata={"source": "faq"})]
    chunks = split_pages(pages)
    assert chunks[0].metadata["source"] == "faq"


def test_never_infinite_loops_on_no_good_boundaries():
    # A single very long "word" with no spaces/periods to break on.
    text = "x" * 5000
    chunks = split_pages([TextPage(text=text, page=1)], chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert sum(len(c.content) for c in chunks) >= len(text)
