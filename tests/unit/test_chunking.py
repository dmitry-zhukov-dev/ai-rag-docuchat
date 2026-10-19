import pytest

from app.rag.chunking import Chunk, chunk_text
from app.rag.loaders import LoadedSegment


# ==========================================
# Basic functionality
# ==========================================

def test_chunk_text_returns_chunks() -> None:
    """Split a long text segment into multiple chunks retaining the page."""
    text = "First sentence. " * 20
    segments = [LoadedSegment(text=text, page=1)]

    chunks = chunk_text(
        segments,
        chunk_size=50,
        chunk_overlap=10,
    )

    assert len(chunks) > 1
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(c.page == 1 for c in chunks)
    assert all(c.text.strip() for c in chunks)


def test_chunk_text_short_text() -> None:
    """Keep a short text in a single chunk."""
    text = "A short document."
    segments = [LoadedSegment(text=text, page=None)]

    assert chunk_text(segments) == [Chunk(text=text, page=None)]


def test_chunk_text_empty_list() -> None:
    """Return an empty list for an empty segment list."""
    assert chunk_text([]) == []


@pytest.mark.parametrize("text", ["   ", "\n\n", "\t  \n"])
def test_chunk_text_whitespace_only(text: str) -> None:
    """Return an empty list for whitespace-only segment text."""
    segments = [LoadedSegment(text=text, page=1)]
    assert chunk_text(segments) == []


def test_chunk_text_preserves_content() -> None:
    """Ensure all source words remain represented in the chunks."""
    text = "alpha beta gamma delta epsilon zeta"
    segments = [LoadedSegment(text=text, page=2)]

    chunks = chunk_text(
        segments,
        chunk_size=12,
        chunk_overlap=3,
    )

    combined_words = " ".join(c.text for c in chunks).split()
    source_words = text.split()

    for word in source_words:
        assert word in combined_words
    assert all(c.page == 2 for c in chunks)


def test_chunk_text_respects_maximum_size() -> None:
    """Ensure every chunk respects the configured character limit."""
    text = "word " * 100
    chunk_size = 30
    segments = [LoadedSegment(text=text, page=1)]

    chunks = chunk_text(
        segments,
        chunk_size=chunk_size,
        chunk_overlap=5,
    )

    assert chunks
    assert all(len(c.text) <= chunk_size for c in chunks)


def test_chunk_text_long_word() -> None:
    """Split a word longer than chunk_size when necessary."""
    text = "a" * 100
    segments = [LoadedSegment(text=text, page=1)]

    chunks = chunk_text(
        segments,
        chunk_size=20,
        chunk_overlap=0,
    )

    assert len(chunks) == 5
    assert all(len(c.text) <= 20 for c in chunks)
    assert "".join(c.text for c in chunks) == text


def test_chunk_text_prefers_paragraph_boundaries() -> None:
    """Prefer paragraph boundaries when they fit the chunk size."""
    text = "First paragraph.\n\nSecond paragraph."
    segments = [LoadedSegment(text=text, page=3)]

    chunks = chunk_text(
        segments,
        chunk_size=25,
        chunk_overlap=0,
    )

    assert chunks == [
        Chunk(text="First paragraph.", page=3),
        Chunk(text="Second paragraph.", page=3),
    ]


def test_chunk_text_preserves_multiple_pages_without_combining() -> None:
    """Ensure chunks from different pages are never combined and retain respective page numbers."""
    segments = [
        LoadedSegment(text="Page one sentence. Another sentence on page one.", page=1),
        LoadedSegment(text="Page two sentence. More text on page two.", page=2),
    ]

    chunks = chunk_text(
        segments,
        chunk_size=25,
        chunk_overlap=5,
    )

    assert all(isinstance(c, Chunk) for c in chunks)
    page_1_chunks = [c for c in chunks if c.page == 1]
    page_2_chunks = [c for c in chunks if c.page == 2]

    assert len(page_1_chunks) >= 2
    assert len(page_2_chunks) >= 2
    # Verify no chunk merges page 1 and page 2 text
    for c in page_1_chunks:
        assert "page two" not in c.text.lower()
    for c in page_2_chunks:
        assert "page one" not in c.text.lower()


# ==========================================
# Input type validation
# ==========================================

@pytest.mark.parametrize("invalid_segments", [None, 123, "text", ["not a segment"]])
def test_chunk_text_rejects_invalid_segments_type(
    invalid_segments: object,
) -> None:
    """Reject inputs that are not lists of LoadedSegment."""
    with pytest.raises(TypeError, match="segments must"):
        chunk_text(invalid_segments)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_size", [1.5, "100", True, None])
def test_chunk_text_rejects_invalid_chunk_size_type(
    invalid_size: object,
) -> None:
    """Require chunk_size to be an integer, not a boolean."""
    with pytest.raises(TypeError, match="chunk_size must be an integer"):
        chunk_text([LoadedSegment(text="Some text", page=1)], chunk_size=invalid_size)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_overlap", [1.5, "10", True, None])
def test_chunk_text_rejects_invalid_overlap_type(
    invalid_overlap: object,
) -> None:
    """Require chunk_overlap to be an integer, not a boolean."""
    with pytest.raises(
        TypeError,
        match="chunk_overlap must be an integer",
    ):
        chunk_text([LoadedSegment(text="Some text", page=1)], chunk_overlap=invalid_overlap)  # type: ignore[arg-type]


# ==========================================
# Parameter validation
# ==========================================

@pytest.mark.parametrize("chunk_size", [0, -1, -100])
def test_chunk_text_rejects_non_positive_chunk_size(
    chunk_size: int,
) -> None:
    """Reject a chunk size that is zero or negative."""
    with pytest.raises(
        ValueError,
        match="chunk_size must be greater than zero",
    ):
        chunk_text([LoadedSegment(text="Some text", page=1)], chunk_size=chunk_size)


@pytest.mark.parametrize("chunk_overlap", [-1, -10])
def test_chunk_text_rejects_negative_overlap(
    chunk_overlap: int,
) -> None:
    """Reject a negative overlap."""
    with pytest.raises(
        ValueError,
        match="chunk_overlap cannot be negative",
    ):
        chunk_text([LoadedSegment(text="Some text", page=1)], chunk_overlap=chunk_overlap)


def test_chunk_text_rejects_overlap_equal_to_chunk_size() -> None:
    """Reject an overlap equal to the chunk size."""
    with pytest.raises(
        ValueError,
        match="chunk_overlap must be smaller than chunk_size",
    ):
        chunk_text(
            [LoadedSegment(text="Some text", page=1)],
            chunk_size=10,
            chunk_overlap=10,
        )


def test_chunk_text_rejects_overlap_larger_than_chunk_size() -> None:
    """Reject an overlap larger than the chunk size."""
    with pytest.raises(
        ValueError,
        match="chunk_overlap must be smaller than chunk_size",
    ):
        chunk_text(
            [LoadedSegment(text="Some text", page=1)],
            chunk_size=10,
            chunk_overlap=11,
        )


def test_chunk_text_allows_zero_overlap() -> None:
    """Allow chunks without overlap."""
    chunks = chunk_text(
        [LoadedSegment(text="alpha beta gamma delta", page=1)],
        chunk_size=10,
        chunk_overlap=0,
    )

    assert len(chunks) > 1
    assert all(c.text.strip() for c in chunks)
    assert all(c.page == 1 for c in chunks)
