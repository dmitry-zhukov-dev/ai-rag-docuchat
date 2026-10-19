import pytest
from pathlib import Path
from pypdf import PdfWriter

from app.rag import loaders
from app.rag.loaders import (
    DocumentLoadError,
    LoadedSegment,
    load_document,
    load_pdf,
    load_txt,
)


# ==========================================
# Tests for load_txt
# ==========================================

def test_load_txt_success(tmp_path: Path) -> None:
    """Read a valid non-empty UTF-8 text file and return a segment with page=None."""
    txt_file = tmp_path / "sample.txt"
    content = "Line 1: Hello World\nLine 2: RAG Pipeline"
    txt_file.write_text(content, encoding="utf-8")

    segments = load_txt(txt_file)
    assert segments == [LoadedSegment(text=content, page=None)]


def test_load_txt_supports_string_path(tmp_path: Path) -> None:
    """Accept a file path provided as a string."""
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("Hello", encoding="utf-8")

    segments = load_txt(str(txt_file))
    assert segments == [LoadedSegment(text="Hello", page=None)]


def test_load_txt_file_not_found(tmp_path: Path) -> None:
    """Raise FileNotFoundError when the file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_txt(tmp_path / "missing.txt")


def test_load_txt_is_directory(tmp_path: Path) -> None:
    """Reject a directory instead of a file."""
    with pytest.raises(IsADirectoryError):
        load_txt(tmp_path)


def test_load_txt_invalid_extension(tmp_path: Path) -> None:
    """Reject unsupported file extensions."""
    invalid_file = tmp_path / "document.doc"
    invalid_file.write_text("Some text", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_txt(invalid_file)


def test_load_txt_uppercase_extension(tmp_path: Path) -> None:
    """Accept an uppercase .TXT extension."""
    txt_file = tmp_path / "sample.TXT"
    txt_file.write_text("Hello", encoding="utf-8")

    segments = load_txt(txt_file)
    assert segments == [LoadedSegment(text="Hello", page=None)]


@pytest.mark.parametrize("content", ["", "   \n\t  "])
def test_load_txt_empty_or_whitespace(
    tmp_path: Path,
    content: str,
) -> None:
    """Reject empty files and files containing only whitespace."""
    txt_file = tmp_path / "empty.txt"
    txt_file.write_text(content, encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="is empty or contains only whitespace",
    ):
        load_txt(txt_file)


def test_load_txt_invalid_utf8(tmp_path: Path) -> None:
    """Raise ValueError when the file cannot be decoded as UTF-8."""
    txt_file = tmp_path / "invalid.txt"
    txt_file.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(ValueError, match="cannot be decoded using UTF-8"):
        load_txt(txt_file)


# ==========================================
# Tests for load_pdf
# ==========================================

def create_blank_pdf(pdf_path: Path) -> None:
    """Create a valid PDF containing one blank page."""
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)

    with pdf_path.open("wb") as file:
        writer.write(file)


def test_load_pdf_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extract and associate text with 1-based page numbers from multiple PDF pages."""
    pdf_path = tmp_path / "sample.pdf"
    create_blank_pdf(pdf_path)

    class FakePage:
        def __init__(self, text: str) -> None:
            self.text = text

        def extract_text(self) -> str:
            return self.text

    class FakeReader:
        def __init__(self, file_path: str) -> None:
            self.pages = [
                FakePage("First page"),
                FakePage("Second page"),
            ]

    monkeypatch.setattr(loaders, "PdfReader", FakeReader)

    segments = load_pdf(pdf_path)

    assert segments == [
        LoadedSegment(text="First page", page=1),
        LoadedSegment(text="Second page", page=2),
    ]


def test_load_pdf_skips_empty_pages_retaining_original_numbers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip empty pages while retaining original 1-based page numbers for non-empty pages."""
    pdf_path = tmp_path / "sample.pdf"
    create_blank_pdf(pdf_path)

    class FakePage:
        def __init__(self, text: str) -> None:
            self.text = text

        def extract_text(self) -> str:
            return self.text

    class FakeReader:
        def __init__(self, file_path: str) -> None:
            self.pages = [
                FakePage(""),  # page 1 empty
                FakePage("Page two text"),  # page 2
                FakePage("   "),  # page 3 whitespace
                FakePage("Page four text"),  # page 4
            ]

    monkeypatch.setattr(loaders, "PdfReader", FakeReader)

    segments = load_pdf(pdf_path)

    assert segments == [
        LoadedSegment(text="Page two text", page=2),
        LoadedSegment(text="Page four text", page=4),
    ]


def test_load_pdf_file_not_found(tmp_path: Path) -> None:
    """Raise FileNotFoundError when the PDF does not exist."""
    with pytest.raises(FileNotFoundError):
        load_pdf(tmp_path / "missing.pdf")


def test_load_pdf_is_directory(tmp_path: Path) -> None:
    """Reject a directory instead of a PDF file."""
    with pytest.raises(IsADirectoryError):
        load_pdf(tmp_path)


def test_load_pdf_invalid_extension(tmp_path: Path) -> None:
    """Reject a file with an unsupported extension."""
    invalid_file = tmp_path / "document.txt"
    invalid_file.write_text("Not a PDF", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_pdf(invalid_file)


def test_load_pdf_uppercase_extension(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accept an uppercase .PDF extension."""
    pdf_path = tmp_path / "sample.PDF"
    create_blank_pdf(pdf_path)

    class FakePage:
        def extract_text(self) -> str:
            return "PDF content"

    class FakeReader:
        def __init__(self, file_path: str) -> None:
            self.pages = [FakePage()]

    monkeypatch.setattr(loaders, "PdfReader", FakeReader)

    segments = load_pdf(pdf_path)
    assert segments == [LoadedSegment(text="PDF content", page=1)]


def test_load_pdf_without_extractable_text(tmp_path: Path) -> None:
    """Reject a valid PDF that contains no extractable text."""
    pdf_path = tmp_path / "blank.pdf"
    create_blank_pdf(pdf_path)

    with pytest.raises(
        ValueError,
        match="contains no extractable text",
    ):
        load_pdf(pdf_path)


def test_load_pdf_corrupted_file(tmp_path: Path) -> None:
    """Raise DocumentLoadError when the PDF cannot be parsed."""
    corrupted_pdf = tmp_path / "corrupted.pdf"
    corrupted_pdf.write_bytes(b"This is not a valid PDF")

    with pytest.raises(DocumentLoadError, match="Failed to read PDF file"):
        load_pdf(corrupted_pdf)


# ==========================================
# Tests for load_document
# ==========================================

def test_load_document_txt(tmp_path: Path) -> None:
    """Dispatch a TXT file to load_txt."""
    txt_file = tmp_path / "document.txt"
    txt_file.write_text("Document text", encoding="utf-8")

    segments = load_document(txt_file)
    assert segments == [LoadedSegment(text="Document text", page=None)]


def test_load_document_pdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dispatch a PDF file to load_pdf."""
    pdf_path = tmp_path / "document.pdf"
    create_blank_pdf(pdf_path)

    def fake_load_pdf(file_path: str | Path) -> list[LoadedSegment]:
        assert Path(file_path) == pdf_path
        return [LoadedSegment(text="Extracted PDF text", page=1)]

    monkeypatch.setattr(loaders, "load_pdf", fake_load_pdf)

    segments = load_document(pdf_path)
    assert segments == [LoadedSegment(text="Extracted PDF text", page=1)]


def test_load_document_uppercase_extension(tmp_path: Path) -> None:
    """Dispatch files correctly when the extension is uppercase."""
    txt_file = tmp_path / "document.TXT"
    txt_file.write_text("Document text", encoding="utf-8")

    segments = load_document(txt_file)
    assert segments == [LoadedSegment(text="Document text", page=None)]


def test_load_document_unsupported_extension(tmp_path: Path) -> None:
    """Reject formats for which no loader is implemented."""
    doc_file = tmp_path / "document.docx"
    doc_file.write_text("Unsupported format", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_document(doc_file)


def test_load_document_missing_file(tmp_path: Path) -> None:
    """Propagate FileNotFoundError from the selected loader."""
    with pytest.raises(FileNotFoundError):
        load_document(tmp_path / "missing.txt")
