from unittest.mock import Mock

import pytest

from app.rag import generation


def _patch_pipeline(monkeypatch, chunks, prompt, answer):
    retrieve_mock = Mock(return_value=chunks)
    prompt_mock = Mock(return_value=prompt)
    generate_mock = Mock(return_value=(answer, None))

    monkeypatch.setattr(generation, "retrieve_chunks", retrieve_mock)
    monkeypatch.setattr(generation, "build_prompt", prompt_mock)
    monkeypatch.setattr(
        generation, "generate_answer_detailed", generate_mock
    )

    return retrieve_mock, prompt_mock, generate_mock


def test_answer_question_returns_structured_result(monkeypatch):
    chunks = [
        {
            "document_id": "doc-1",
            "chunk_id": "doc-1:0",
            "filename": "manual.pdf",
            "page": 2,
            "text": "RAG stands for Retrieval-Augmented Generation.",
            "score": 0.9,
        }
    ]

    retrieve_mock, prompt_mock, generate_mock = _patch_pipeline(
        monkeypatch, chunks, "Test prompt", "Generated answer"
    )

    result = generation.answer_question(
        question="What does RAG stand for?",
        workspace_id="ws-1",
        limit=3,
        document_id="doc-1",
    )

    assert result.answer == "Generated answer"
    assert result.insufficient_context is False
    assert result.chunks == chunks

    assert result.sources == [
        {
            "document_id": "doc-1",
            "filename": "manual.pdf",
            "page": 2,
            "chunk_id": "doc-1:0",
            "snippet": "RAG stands for Retrieval-Augmented Generation.",
        }
    ]

    retrieve_mock.assert_called_once_with(
        question="What does RAG stand for?",
        workspace_id="ws-1",
        limit=3,
        document_id="doc-1",
        document_ids=None,
    )
    prompt_mock.assert_called_once_with(
        question="What does RAG stand for?",
        context_chunks=chunks,
        history=None,
    )
    generate_mock.assert_called_once_with("Test prompt")


def test_answer_question_reports_insufficient_context_on_empty_retrieval(
    monkeypatch,
):
    retrieve_mock, prompt_mock, generate_mock = _patch_pipeline(
        monkeypatch, [], "Prompt without context", "Unused answer"
    )

    result = generation.answer_question(
        "Unknown question", workspace_id="ws-1"
    )

    assert result.insufficient_context is True
    assert result.answer == ""
    assert result.sources == []

    retrieve_mock.assert_called_once()
    prompt_mock.assert_not_called()
    generate_mock.assert_not_called()


def test_answer_question_reports_insufficient_context_when_all_chunks_dropped(
    monkeypatch,
):
    chunks = [
        {
            "document_id": "doc-9",
            "chunk_id": "doc-9:0",
            "text": "Other workspace text.",
        }
    ]

    retrieve_mock, prompt_mock, generate_mock = _patch_pipeline(
        monkeypatch, chunks, "Prompt", "Unused answer"
    )

    result = generation.answer_question(
        question="Question",
        workspace_id="ws-1",
        accessible_document_ids={"doc-1"},
    )

    assert result.insufficient_context is True
    assert result.answer == ""
    assert result.sources == []

    prompt_mock.assert_not_called()
    generate_mock.assert_not_called()


def test_answer_question_truncates_long_snippets(monkeypatch):
    long_text = "word " * 200
    chunks = [
        {
            "document_id": "doc-1",
            "chunk_id": "doc-1:0",
            "filename": "big.txt",
            "page": None,
            "text": long_text,
        }
    ]

    _patch_pipeline(monkeypatch, chunks, "Prompt", "Answer")

    result = generation.answer_question(
        question="Question", workspace_id="ws-1"
    )

    assert result.insufficient_context is False
    assert (
        len(result.sources[0]["snippet"])
        <= generation.SNIPPET_MAX_LENGTH + 1
    )
    assert result.sources[0]["snippet"].endswith("…")


def test_answer_question_propagates_retrieval_error(monkeypatch):
    retrieve_mock = Mock(side_effect=RuntimeError("Retrieval failed"))
    prompt_mock = Mock()
    generate_mock = Mock()

    monkeypatch.setattr(generation, "retrieve_chunks", retrieve_mock)
    monkeypatch.setattr(generation, "build_prompt", prompt_mock)
    monkeypatch.setattr(generation, "generate_answer_detailed", generate_mock)

    with pytest.raises(RuntimeError, match="Retrieval failed"):
        generation.answer_question(
            "What does RAG mean?", workspace_id="ws-1"
        )

    prompt_mock.assert_not_called()
    generate_mock.assert_not_called()


def test_answer_question_propagates_generation_error(monkeypatch):
    chunks = [{"document_id": "doc-1", "text": "Some context"}]

    retrieve_mock, prompt_mock, generate_mock = _patch_pipeline(
        monkeypatch, chunks, "Test prompt", None
    )
    generate_mock.side_effect = RuntimeError("Gemini failed")

    with pytest.raises(RuntimeError, match="Gemini failed"):
        generation.answer_question(
            "What does RAG mean?", workspace_id="ws-1"
        )

    retrieve_mock.assert_called_once()
    prompt_mock.assert_called_once()
    generate_mock.assert_called_once_with("Test prompt")


def test_answer_question_traces_without_breaking(
    monkeypatch,
):
    """Broken or inactive tracing never breaks answers."""
    from app.integrations import langfuse

    monkeypatch.setattr(
        langfuse.settings, "langfuse_enabled", True
    )
    monkeypatch.setattr(
        langfuse.tracer, "_get_client", lambda: None
    )

    chunks = [
        {
            "document_id": "doc-1",
            "chunk_id": "doc-1:0",
            "filename": "manual.pdf",
            "page": 1,
            "text": "Context text",
        }
    ]

    retrieve_mock, prompt_mock, generate_mock = (
        _patch_pipeline(monkeypatch, chunks, "Prompt", "Answer")
    )

    result = generation.answer_question(
        question="Question",
        workspace_id="ws-1",
    )

    assert result.answer == "Answer"
    assert result.insufficient_context is False
