
import pytest
from pathlib import Path
from pypdf import PdfWriter

from app.rag import loaders
from app.rag.loaders import (
    DocumentLoadError,
    load_document,
    load_pdf,
    load_txt,
)


# ==========================================
# Tests for load_txt
# ==========================================

def test_load_txt_success(tmp_path: Path) -> None:
    """Read a valid non-empty UTF-8 text file."""
    txt_file = tmp_path / "sample.txt"
    content = "Line 1: Hello World\nLine 2: RAG Pipeline"
    txt_file.write_text(content, encoding="utf-8")

    assert load_txt(txt_file) == content


def test_load_txt_supports_string_path(tmp_path: Path) -> None:
    """Accept a file path provided as a string."""
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("Hello", encoding="utf-8")

    assert load_txt(str(txt_file)) == "Hello"


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

    assert load_txt(txt_file) == "Hello"


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
    """Extract and combine text from multiple PDF pages."""
    pdf_path = tmp_path / "sample.pdf"
    create_blank_pdf(pdf_path)

    # Simulate pages containing extracted text.
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

    result = load_pdf(pdf_path)

    assert result == "First page\n\nSecond page"


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

    assert load_pdf(pdf_path) == "PDF content"


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

    assert load_document(txt_file) == "Document text"


def test_load_document_pdf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dispatch a PDF file to load_pdf."""
    pdf_path = tmp_path / "document.pdf"
    create_blank_pdf(pdf_path)

    def fake_load_pdf(file_path: str | Path) -> str:
        assert Path(file_path) == pdf_path
        return "Extracted PDF text"

    monkeypatch.setattr(loaders, "load_pdf", fake_load_pdf)

    assert load_document(pdf_path) == "Extracted PDF text"


def test_load_document_uppercase_extension(tmp_path: Path) -> None:
    """Dispatch files correctly when the extension is uppercase."""
    txt_file = tmp_path / "document.TXT"
    txt_file.write_text("Document text", encoding="utf-8")

    assert load_document(txt_file) == "Document text"


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
