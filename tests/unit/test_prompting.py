
import pytest

from app.rag.prompting import build_prompt


def test_build_prompt_includes_question_and_context():
    prompt = build_prompt(
        question="What is RAG?",
        context_chunks=[
            {"text": "RAG stands for Retrieval-Augmented Generation."}
        ],
    )

    assert "What is RAG?" in prompt
    assert "RAG stands for Retrieval-Augmented Generation." in prompt
    assert "Do not invent facts" in prompt


def test_build_prompt_without_context():
    prompt = build_prompt(
        question="What is RAG?",
        context_chunks=[],
    )

    assert "No relevant context was found." in prompt


def test_build_prompt_rejects_empty_question():
    with pytest.raises(ValueError):
        build_prompt("  ", [])


def test_build_prompt_rejects_invalid_chunk():
    with pytest.raises(ValueError):
        build_prompt("What is RAG?", [{"text": ""}])
