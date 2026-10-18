
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150,
) -> list[str]:
    """
    Split text into chunks while preserving natural text boundaries.

    The splitter prefers paragraph breaks, line breaks, spaces,
    and finally individual characters.

    Args:
        text: Source text to split.
        chunk_size: Maximum chunk size measured in characters.
        chunk_overlap: Desired overlap between consecutive chunks.

    Returns:
        A list of non-empty text chunks.

    Raises:
        TypeError: If text or numeric parameters have invalid types.
        ValueError: If chunk_size or chunk_overlap is out of range.
    """
    # Validate the source text.
    if not isinstance(text, str):
        raise TypeError("text must be a string.")

    # Reject booleans and non-integer values explicitly.
    # In Python, bool is a subclass of int, so isinstance alone
    # would also accept True and False.
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
    if not text.strip():
        return []

    # Configure the splitter to prefer natural text boundaries.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
        strip_whitespace=True,
    )

    # Split the text and return the resulting chunks.
    return splitter.split_text(text)
