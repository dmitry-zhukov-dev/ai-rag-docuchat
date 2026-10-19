from unittest.mock import patch

import pytest

from app.rag import ingestion
from app.rag.chunking import Chunk
from app.rag.loaders import LoadedSegment


@patch("app.rag.ingestion.save_chunks")
@patch("app.rag.ingestion.embed_texts")
@patch("app.rag.ingestion.chunk_text")
@patch("app.rag.ingestion.load_document")
def test_ingest_document_processes_and_saves_chunks(
    mock_load,
    mock_chunk,
    mock_embed,
    mock_save,
):
    mock_load.return_value = [LoadedSegment(text="Document text", page=1)]
    chunks = [
        Chunk(text="First chunk", page=1),
        Chunk(text="Second chunk", page=1),
    ]
    mock_chunk.return_value = chunks
    mock_embed.return_value = [[0.1] * 384, [0.2] * 384]

    result = ingestion.ingest_document(
        file_path="sample.pdf",
        document_id="doc-1",
    )

    assert result == 2
    mock_load.assert_called_once_with("sample.pdf")
    mock_chunk.assert_called_once_with([LoadedSegment(text="Document text", page=1)])
    mock_embed.assert_called_once_with(["First chunk", "Second chunk"])
    mock_save.assert_called_once_with(
        document_id="doc-1",
        chunks=chunks,
        vectors=[[0.1] * 384, [0.2] * 384],
    )


@patch("app.rag.ingestion.save_chunks")
@patch("app.rag.ingestion.embed_texts")
@patch("app.rag.ingestion.chunk_text")
@patch("app.rag.ingestion.load_document")
def test_ingest_document_returns_zero_when_no_chunks(
    mock_load,
    mock_chunk,
    mock_embed,
    mock_save,
):
    mock_load.return_value = []
    mock_chunk.return_value = []

    result = ingestion.ingest_document(
        file_path="empty.txt",
        document_id="doc-2",
    )

    assert result == 0
    mock_embed.assert_not_called()
    mock_save.assert_not_called()


@patch("app.rag.ingestion.save_chunks")
@patch("app.rag.ingestion.embed_texts")
@patch("app.rag.ingestion.chunk_text")
@patch("app.rag.ingestion.load_document")
def test_ingest_document_stops_if_loading_fails(
    mock_load,
    mock_chunk,
    mock_embed,
    mock_save,
):
    mock_load.side_effect = ValueError("Unsupported file type")

    with pytest.raises(ValueError, match="Unsupported file type"):
        ingestion.ingest_document(
            file_path="image.png",
            document_id="doc-3",
        )

    mock_chunk.assert_not_called()
    mock_embed.assert_not_called()
    mock_save.assert_not_called()


@patch("app.rag.ingestion.save_chunks")
@patch("app.rag.ingestion.embed_texts")
@patch("app.rag.ingestion.chunk_text")
@patch("app.rag.ingestion.load_document")
def test_ingest_document_stops_if_embedding_fails(
    mock_load,
    mock_chunk,
    mock_embed,
    mock_save,
):
    mock_load.return_value = [LoadedSegment(text="Document text", page=None)]
    chunks = [Chunk(text="First chunk", page=None)]
    mock_chunk.return_value = chunks
    mock_embed.side_effect = RuntimeError("Embedding failed")

    with pytest.raises(RuntimeError, match="Embedding failed"):
        ingestion.ingest_document(
            file_path="sample.txt",
            document_id="doc-4",
        )

    mock_save.assert_not_called()


@patch("app.rag.ingestion.save_chunks")
@patch("app.rag.ingestion.embed_texts")
@patch("app.rag.ingestion.chunk_text")
@patch("app.rag.ingestion.load_document")
def test_ingest_document_returns_chunk_count(
    mock_load,
    mock_chunk,
    mock_embed,
    mock_save,
):
    mock_load.return_value = [LoadedSegment(text="Document text", page=1)]
    chunks = [Chunk(text="Only chunk", page=1)]
    mock_chunk.return_value = chunks
    mock_embed.return_value = [[0.1] * 384]

    result = ingestion.ingest_document(
        file_path="sample.pdf",
        document_id="doc-5",
    )

    assert result == 1
