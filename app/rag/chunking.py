from dataclasses import dataclass
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.loaders import LoadedSegment


@dataclass(frozen=True)
class Chunk:
    """Represents a text chunk with its source page number."""

    text: str
    page: int | None


def chunk_text(
    segments: list[LoadedSegment],
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    """
    Split loaded document segments into chunks while preserving natural text boundaries
    and page boundaries.

    Args:
        segments: List of LoadedSegment objects to split.
        chunk_size: Maximum chunk size measured in characters.
        chunk_overlap: Desired overlap between consecutive chunks.

    Returns:
        A list of non-empty Chunk objects.

    Raises:
        TypeError: If segments or numeric parameters have invalid types.
        ValueError: If chunk_size or chunk_overlap is out of range.
    """
    # Validate segments input.
    if not isinstance(segments, list):
        raise TypeError("segments must be a list of LoadedSegment instances.")

    for segment in segments:
        if not isinstance(segment, LoadedSegment):
            raise TypeError("segments must contain only LoadedSegment instances.")

    # Reject booleans and non-integer values explicitly.
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int):
        raise TypeError("chunk_size must be an integer.")

    if isinstance(chunk_overlap, bool) or not isinstance(
        chunk_overlap, int
    ):
        raise TypeError("chunk_overlap must be an integer.")

    # Validate the chunk size and overlap relationship.
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap cannot be negative.")

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap must be smaller than chunk_size."
        )

    # Return an empty list for empty or whitespace-only input.
    if not segments:
        return []

    # Configure the splitter to prefer natural text boundaries.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
        strip_whitespace=True,
    )

    chunks = []
    for segment in segments:
        if not segment.text or not segment.text.strip():
            continue
        page_texts = splitter.split_text(segment.text)
        for text in page_texts:
            if text and text.strip():
                chunks.append(Chunk(text=text.strip(), page=segment.page))

    return chunks
