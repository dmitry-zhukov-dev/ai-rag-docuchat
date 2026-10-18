
import pytest

from app.rag.chunking import chunk_text


# ==========================================
# Basic functionality
# ==========================================

def test_chunk_text_returns_chunks() -> None:
    """Split a long text into multiple chunks."""
    text = "First sentence. " * 20

    chunks = chunk_text(
        text,
        chunk_size=50,
        chunk_overlap=10,
    )

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_chunk_text_short_text() -> None:
    """Keep a short text in a single chunk."""
    text = "A short document."

    assert chunk_text(text) == [text]


def test_chunk_text_empty_string() -> None:
    """Return an empty list for an empty string."""
    assert chunk_text("") == []


@pytest.mark.parametrize("text", ["   ", "\n\n", "\t  \n"])
def test_chunk_text_whitespace_only(text: str) -> None:
    """Return an empty list for whitespace-only input."""
    assert chunk_text(text) == []


def test_chunk_text_preserves_content() -> None:
    """Ensure all source words remain represented in the chunks."""
    text = "alpha beta gamma delta epsilon zeta"

    chunks = chunk_text(
        text,
        chunk_size=12,
        chunk_overlap=3,
    )

    combined_words = " ".join(chunks).split()
    source_words = text.split()

    for word in source_words:
        assert word in combined_words


def test_chunk_text_respects_maximum_size() -> None:
    """Ensure every chunk respects the configured character limit."""
    text = "word " * 100
    chunk_size = 30

    chunks = chunk_text(
        text,
        chunk_size=chunk_size,
        chunk_overlap=5,
    )

    assert chunks
    assert all(len(chunk) <= chunk_size for chunk in chunks)


def test_chunk_text_long_word() -> None:
    """Split a word longer than chunk_size when necessary."""
    text = "a" * 100

    chunks = chunk_text(
        text,
        chunk_size=20,
        chunk_overlap=0,
    )

    assert len(chunks) == 5
    assert all(len(chunk) <= 20 for chunk in chunks)
    assert "".join(chunks) == text


def test_chunk_text_prefers_paragraph_boundaries() -> None:
    """Prefer paragraph boundaries when they fit the chunk size."""
    text = "First paragraph.\n\nSecond paragraph."

    chunks = chunk_text(
        text,
        chunk_size=25,
        chunk_overlap=0,
    )

    assert chunks == [
        "First paragraph.",
        "Second paragraph.",
    ]


# ==========================================
# Input type validation
# ==========================================

@pytest.mark.parametrize("invalid_text", [None, 123, ["text"], b"text"])
def test_chunk_text_rejects_invalid_text_type(
    invalid_text: object,
) -> None:
    """Reject inputs that are not strings."""
    with pytest.raises(TypeError, match="text must be a string"):
        chunk_text(invalid_text)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_size", [1.5, "100", True, None])
def test_chunk_text_rejects_invalid_chunk_size_type(
    invalid_size: object,
) -> None:
    """Require chunk_size to be an integer, not a boolean."""
    with pytest.raises(TypeError, match="chunk_size must be an integer"):
        chunk_text("Some text", chunk_size=invalid_size)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_overlap", [1.5, "10", True, None])
def test_chunk_text_rejects_invalid_overlap_type(
    invalid_overlap: object,
) -> None:
    """Require chunk_overlap to be an integer, not a boolean."""
    with pytest.raises(
        TypeError,
        match="chunk_overlap must be an integer",
    ):
        chunk_text("Some text", chunk_overlap=invalid_overlap)  # type: ignore[arg-type]


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
        chunk_text("Some text", chunk_size=chunk_size)


@pytest.mark.parametrize("chunk_overlap", [-1, -10])
def test_chunk_text_rejects_negative_overlap(
    chunk_overlap: int,
) -> None:
    """Reject a negative overlap."""
    with pytest.raises(
        ValueError,
        match="chunk_overlap cannot be negative",
    ):
        chunk_text("Some text", chunk_overlap=chunk_overlap)


def test_chunk_text_rejects_overlap_equal_to_chunk_size() -> None:
    """Reject an overlap equal to the chunk size."""
    with pytest.raises(
        ValueError,
        match="chunk_overlap must be smaller than chunk_size",
    ):
        chunk_text(
            "Some text",
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
            "Some text",
            chunk_size=10,
            chunk_overlap=11,
        )


def test_chunk_text_allows_zero_overlap() -> None:
    """Allow chunks without overlap."""
    chunks = chunk_text(
        "alpha beta gamma delta",
        chunk_size=10,
        chunk_overlap=0,
    )

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
