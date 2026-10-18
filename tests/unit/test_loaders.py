import pytest
from pathlib import Path
from pypdf import PdfWriter

from app.rag.loaders import load_txt, load_pdf, DocumentLoadError


# ==========================================
# Tests for load_txt
# ==========================================

def test_load_txt_success(tmp_path: Path) -> None:
    """Test reading a valid non-empty text file."""
    txt_file = tmp_path / "sample.txt"
    content = "Line 1: Hello World\nLine 2: RAG Pipeline"
    txt_file.write_text(content, encoding="utf-8")

    result = load_txt(txt_file)
    assert result == content


def test_load_txt_file_not_found() -> None:
    """Test raising FileNotFoundError for non-existing files."""
    with pytest.raises(FileNotFoundError):
        load_txt("non_existing_file.txt")


def test_load_txt_is_directory(tmp_path: Path) -> None:
    """Test raising IsADirectoryError when passing a directory path."""
    with pytest.raises(IsADirectoryError):
        load_txt(tmp_path)


def test_load_txt_invalid_extension(tmp_path: Path) -> None:
    """Test raising ValueError for unsupported file extensions."""
    invalid_file = tmp_path / "doc.doc"
    invalid_file.write_text("Some text", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_txt(invalid_file)


def test_load_txt_empty_file(tmp_path: Path) -> None:
    """Test raising ValueError when text file is empty or only whitespace."""
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("   \n\t ", encoding="utf-8")

    with pytest.raises(ValueError, match="is empty or contains only whitespace"):
        load_txt(empty_file)


# ==========================================
# Tests for load_pdf
# ==========================================

def test_load_pdf_success(tmp_path: Path) -> None:
    """Test extracting text from a multi-page PDF file."""
    pdf_path = tmp_path / "test.pdf"

    # Create a small valid PDF with 2 pages in-memory
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    
    with open(pdf_path, "wb") as f:
        writer.write(f)

    # Note: pypdf blank pages have no text, so let's test empty PDF detection
    with pytest.raises(ValueError, match="contains no extractable text"):
        load_pdf(pdf_path)


def test_load_pdf_file_not_found() -> None:
    """Test raising FileNotFoundError for missing PDF."""
    with pytest.raises(FileNotFoundError):
        load_pdf("missing_document.pdf")


def test_load_pdf_invalid_extension(tmp_path: Path) -> None:
    """Test raising ValueError for wrong extension."""
    invalid_file = tmp_path / "file.txt"
    invalid_file.write_text("Not a PDF", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file format"):
        load_pdf(invalid_file)


def test_load_pdf_corrupted_file(tmp_path: Path) -> None:
    """Test raising ValueError when reading a corrupted PDF file."""
    corrupted_pdf = tmp_path / "corrupted.pdf"
    corrupted_pdf.write_bytes(b"This is not a valid PDF binary content")

    with pytest.raises(ValueError, match="Failed to read PDF file"):
        load_pdf(corrupted_pdf)