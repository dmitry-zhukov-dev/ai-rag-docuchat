
from unittest.mock import Mock

import pytest

from app.rag import generation


def test_answer_question_returns_generated_answer(monkeypatch):
    chunks = [
        {
            "text": "RAG stands for Retrieval-Augmented Generation.",
            "score": 0.9,
        }
    ]
    prompt = "Test prompt"
    expected_answer = "RAG stands for Retrieval-Augmented Generation."

    retrieve_mock = Mock(return_value=chunks)
    prompt_mock = Mock(return_value=prompt)
    generate_mock = Mock(return_value=expected_answer)

    monkeypatch.setattr(generation, "retrieve_chunks", retrieve_mock)
    monkeypatch.setattr(generation, "build_prompt", prompt_mock)
    monkeypatch.setattr(generation, "generate_answer", generate_mock)

    result = generation.answer_question(
        question="What does RAG stand for?",
        limit=3,
        document_id="test-document",
    )

    assert result == expected_answer

    retrieve_mock.assert_called_once_with(
        question="What does RAG stand for?",
        limit=3,
        document_id="test-document",
    )
    prompt_mock.assert_called_once_with(
        question="What does RAG stand for?",
        context_chunks=chunks,
    )
    generate_mock.assert_called_once_with(prompt)


def test_answer_question_passes_empty_context_to_prompt(monkeypatch):
    retrieve_mock = Mock(return_value=[])
    prompt_mock = Mock(return_value="Prompt without context")
    generate_mock = Mock(return_value="I could not find the answer.")

    monkeypatch.setattr(generation, "retrieve_chunks", retrieve_mock)
    monkeypatch.setattr(generation, "build_prompt", prompt_mock)
    monkeypatch.setattr(generation, "generate_answer", generate_mock)

    result = generation.answer_question("Unknown question")

    assert result == "I could not find the answer."
    prompt_mock.assert_called_once_with(
        question="Unknown question",
        context_chunks=[],
    )
    generate_mock.assert_called_once_with("Prompt without context")


def test_answer_question_propagates_retrieval_error(monkeypatch):
    retrieve_mock = Mock(side_effect=RuntimeError("Retrieval failed"))
    prompt_mock = Mock()
    generate_mock = Mock()

    monkeypatch.setattr(generation, "retrieve_chunks", retrieve_mock)
    monkeypatch.setattr(generation, "build_prompt", prompt_mock)
    monkeypatch.setattr(generation, "generate_answer", generate_mock)

    with pytest.raises(RuntimeError, match="Retrieval failed"):
        generation.answer_question("What does RAG mean?")

    prompt_mock.assert_not_called()
    generate_mock.assert_not_called()


def test_answer_question_propagates_generation_error(monkeypatch):
    retrieve_mock = Mock(return_value=[{"text": "Some context"}])
    prompt_mock = Mock(return_value="Test prompt")
    generate_mock = Mock(side_effect=RuntimeError("Gemini failed"))

    monkeypatch.setattr(generation, "retrieve_chunks", retrieve_mock)
    monkeypatch.setattr(generation, "build_prompt", prompt_mock)
    monkeypatch.setattr(generation, "generate_answer", generate_mock)

    with pytest.raises(RuntimeError, match="Gemini failed"):
        generation.answer_question("What does RAG mean?")

    retrieve_mock.assert_called_once()
    prompt_mock.assert_called_once()
    generate_mock.assert_called_once_with("Test prompt")
