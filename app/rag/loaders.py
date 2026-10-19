from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


@dataclass(frozen=True)
class LoadedSegment:
    """Represents a text segment with its source page number."""

    text: str
    page: int | None


class DocumentLoadError(Exception):
    """Base exception for document loading errors."""

    pass


def load_txt(file_path: str | Path) -> list[LoadedSegment]:
    """
    Load text from a UTF-8 text file as a single segment with page=None.

    Args:
        file_path: Path to the text file (.txt).

    Returns:
        A list containing a single LoadedSegment.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory.
        ValueError: If the extension is invalid, encoding is broken,
            or the file is empty.
        PermissionError: If read permissions are missing.
        DocumentLoadError: If an unexpected reading error occurs.
    """
    path = Path(file_path)

    # Check that the path exists and points to a file.
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise IsADirectoryError(
            f"Path points to a directory instead of a file: {path}"
        )

    # Validate the extension, ignoring letter case.
    if path.suffix.lower() != ".txt":
        raise ValueError(
            f"Unsupported file format: '{path.suffix}'. "
            "Expected a '.txt' file."
        )

    # Read the file using UTF-8 encoding.
    try:
        content = path.read_text(encoding="utf-8")
    except PermissionError as e:
        raise PermissionError(
            f"Permission denied to read file: {path}"
        ) from e
    except UnicodeDecodeError as e:
        raise ValueError(
            f"File {path} cannot be decoded using UTF-8. "
            "Ensure the file uses the correct encoding."
        ) from e
    except OSError as e:
        raise DocumentLoadError(
            f"Failed to read file {path}: {e}"
        ) from e

    # Reject empty files and files containing only whitespace.
    if not content.strip():
        raise ValueError(
            f"The loaded file {path} is empty or contains only whitespace."
        )

    return [LoadedSegment(text=content, page=None)]


def load_pdf(file_path: str | Path) -> list[LoadedSegment]:
    """
    Extract text from a PDF file into page-associated segments.

    Args:
        file_path: Path to the PDF file (.pdf).

    Returns:
        A list of LoadedSegment objects containing page text and 1-based page numbers.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory.
        ValueError: If the extension is invalid or no text can be extracted.
        PermissionError: If read permissions are missing.
        DocumentLoadError: If the PDF cannot be read or parsed.
    """
    path = Path(file_path)

    # Check that the path exists and points to a file.
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if not path.is_file():
        raise IsADirectoryError(
            f"Path points to a directory instead of a file: {path}"
        )

    # Validate the extension, ignoring letter case.
    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Unsupported file format: '{path.suffix}'. "
            "Expected a '.pdf' file."
        )

    # Open the PDF and initialize the reader.
    try:
        reader = PdfReader(str(path))
    except PermissionError as e:
        raise PermissionError(
            f"Permission denied to read PDF file: {path}"
        ) from e
    except (PdfReadError, OSError) as e:
        raise DocumentLoadError(
            f"Failed to read PDF file {path}: {e}"
        ) from e

    # Extract text from each page, skipping pages without readable text.
    segments = []

    try:
        for index, page in enumerate(reader.pages):
            page_text = page.extract_text()

            if page_text and page_text.strip():
                # 1-based page number
                segments.append(LoadedSegment(text=page_text.strip(), page=index + 1))

    except (PdfReadError, OSError) as e:
        raise DocumentLoadError(
            f"Failed to extract text from PDF file {path}: {e}"
        ) from e

    # Scanned PDFs may contain images without extractable text.
    if not segments:
        raise ValueError(
            f"PDF file {path} contains no extractable text. "
            "It may consist only of scanned images."
        )

    return segments


def load_document(file_path: str | Path) -> list[LoadedSegment]:
    """
    Select the appropriate loader based on the file extension.

    Args:
        file_path: Path to a supported document (.txt or .pdf).

    Returns:
        A list of LoadedSegment objects extracted from the document.

    Raises:
        ValueError: If the file format is unsupported.
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path points to a directory.
        PermissionError: If read permissions are missing.
        DocumentLoadError: If an unexpected loading error occurs.
    """
    # Normalize the path and determine its extension.
    path = Path(file_path)
    extension = path.suffix.lower()

    # Dispatch the file to the appropriate loader.
    if extension == ".txt":
        return load_txt(path)

    if extension == ".pdf":
        return load_pdf(path)

    # Reject unsupported formats.
    raise ValueError(
        f"Unsupported file format: '{extension}'. "
        "Supported formats: .txt, .pdf."
    )
