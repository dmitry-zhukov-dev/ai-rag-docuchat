from unittest.mock import patch

import pytest

from app.rag import retrieval


@patch("app.rag.retrieval.search_chunks")
@patch("app.rag.retrieval.embed_query")
def test_retrieve_chunks_passes_workspace_to_search(mock_embed, mock_search):
    mock_embed.return_value = [0.1] * 384
    mock_search.return_value = []

    result = retrieval.retrieve_chunks(
        question="What is RAG?",
        workspace_id="ws-1",
        limit=3,
    )

    assert result == []
    mock_embed.assert_called_once_with("What is RAG?")
    mock_search.assert_called_once_with(
        query_vector=[0.1] * 384,
        workspace_id="ws-1",
        limit=3,
        document_id=None,
        document_ids=None,
    )


@patch("app.rag.retrieval.search_chunks")
@patch("app.rag.retrieval.embed_query")
def test_retrieve_chunks_passes_document_restrictions(mock_embed, mock_search):
    mock_embed.return_value = [0.1] * 384
    mock_search.return_value = []

    retrieval.retrieve_chunks(
        question="What is RAG?",
        workspace_id="ws-1",
        document_id="doc-1",
    )

    mock_search.assert_called_once_with(
        query_vector=[0.1] * 384,
        workspace_id="ws-1",
        limit=5,
        document_id="doc-1",
        document_ids=None,
    )

    retrieval.retrieve_chunks(
        question="What is RAG?",
        workspace_id="ws-1",
        document_ids=["doc-1", "doc-2"],
    )

    mock_search.assert_called_with(
        query_vector=[0.1] * 384,
        workspace_id="ws-1",
        limit=5,
        document_id=None,
        document_ids=["doc-1", "doc-2"],
    )


@patch("app.rag.retrieval.search_chunks")
@patch("app.rag.retrieval.embed_query")
def test_retrieve_chunks_propagates_empty_result_set(mock_embed, mock_search):
    mock_embed.return_value = [0.1] * 384
    mock_search.return_value = []

    assert (
        retrieval.retrieve_chunks(
            question="Unknown topic",
            workspace_id="ws-1",
        )
        == []
    )


def test_retrieve_chunks_rejects_empty_question():
    with pytest.raises(ValueError, match="question"):
        retrieval.retrieve_chunks(
            question="   ",
            workspace_id="ws-1",
        )


@pytest.mark.parametrize("workspace_id", ["", "   ", 123, None])
def test_retrieve_chunks_rejects_invalid_workspace_id(workspace_id):
    with pytest.raises(ValueError, match="workspace_id"):
        retrieval.retrieve_chunks(
            question="What is RAG?",
            workspace_id=workspace_id,  # type: ignore[arg-type]
        )


# ==========================================
# Source consistency verification
# ==========================================

def test_verify_chunks_keeps_accessible_documents():
    chunks = [
        {"chunk_id": "doc-1:0", "document_id": "doc-1", "text": "a"},
        {"chunk_id": "doc-2:0", "document_id": "doc-2", "text": "b"},
    ]

    verified, diagnostics = retrieval.verify_chunks(
        chunks, {"doc-1", "doc-2"}
    )

    assert verified == chunks
    assert diagnostics == []


def test_verify_chunks_drops_inaccessible_documents():
    chunks = [
        {"chunk_id": "doc-1:0", "document_id": "doc-1", "text": "a"},
        {"chunk_id": "doc-9:0", "document_id": "doc-9", "text": "b"},
    ]

    verified, diagnostics = retrieval.verify_chunks(chunks, {"doc-1"})

    assert verified == [chunks[0]]
    assert diagnostics == [
        {
            "chunk_id": "doc-9:0",
            "document_id": "doc-9",
            "reason": "document_not_accessible",
        }
    ]


def test_verify_chunks_drops_chunks_without_document_id():
    chunks = [
        {"chunk_id": "doc-1:0", "document_id": None, "text": "a"},
        {"chunk_id": "doc-1:1", "text": "b"},
    ]

    verified, diagnostics = retrieval.verify_chunks(chunks, {"doc-1"})

    assert verified == []
    assert len(diagnostics) == 2
    assert diagnostics[0]["reason"] == "missing_document_id"
    assert diagnostics[1]["reason"] == "missing_document_id"


def test_verify_chunks_preserves_result_ordering():
    chunks = [
        {"chunk_id": "doc-2:0", "document_id": "doc-2", "text": "a"},
        {"chunk_id": "doc-1:0", "document_id": "doc-1", "text": "b"},
        {"chunk_id": "doc-3:0", "document_id": "doc-3", "text": "c"},
    ]

    verified, diagnostics = retrieval.verify_chunks(
        chunks, {"doc-1", "doc-3"}
    )

    assert [chunk["chunk_id"] for chunk in verified] == [
        "doc-1:0",
        "doc-3:0",
    ]
    assert diagnostics[0]["chunk_id"] == "doc-2:0"


def test_verify_chunks_accepts_empty_input():
    verified, diagnostics = retrieval.verify_chunks([], set())

    assert verified == []
    assert diagnostics == []


@pytest.mark.parametrize("chunks", [None, "chunks", {"a": 1}])
def test_verify_chunks_rejects_invalid_chunks_type(chunks):
    with pytest.raises(TypeError, match="chunks must be a list"):
        retrieval.verify_chunks(chunks, {"doc-1"})


@pytest.mark.parametrize(
    "accessible", [["doc-1"], "doc-1", None, {"doc-1": 1}]
)
def test_verify_chunks_rejects_invalid_accessible_type(accessible):
    with pytest.raises(
        TypeError, match="accessible_document_ids must be a set"
    ):
        retrieval.verify_chunks([], accessible)


def test_verify_chunks_rejects_non_dict_chunk():
    with pytest.raises(TypeError, match="each chunk must be a dictionary"):
        retrieval.verify_chunks(["not-a-chunk"], {"doc-1"})
