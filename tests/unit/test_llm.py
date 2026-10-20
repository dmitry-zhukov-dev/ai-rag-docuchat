from unittest.mock import MagicMock, patch

import pytest

from app.integrations import llm
from app.integrations.llm import GenerationError, generate_answer


def _client_with_answer(text: str) -> MagicMock:
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(
        text=text
    )
    return client


@patch("app.integrations.llm._get_client")
def test_generate_answer_returns_provider_text(mock_get_client):
    mock_get_client.return_value = _client_with_answer("The answer")

    assert generate_answer("A prompt") == "The answer"

    call = (
        mock_get_client.return_value.models.generate_content.call_args
    )
    assert call.kwargs["model"] == llm.MODEL_NAME
    assert call.kwargs["contents"] == "A prompt"


@patch("app.integrations.llm._get_client")
def test_generate_answer_strips_whitespace(mock_get_client):
    mock_get_client.return_value = _client_with_answer("  padded  ")

    assert generate_answer("A prompt") == "padded"


def test_generate_answer_rejects_invalid_prompt():
    with pytest.raises(TypeError, match="prompt must be a string"):
        generate_answer(123)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="prompt cannot be empty"):
        generate_answer("   ")


@patch("app.integrations.llm._get_client")
def test_generate_answer_wraps_provider_errors(mock_get_client):
    mock_get_client.return_value.models.generate_content.side_effect = (
        RuntimeError("Provider timeout with internals")
    )

    with pytest.raises(GenerationError, match="could not be generated"):
        generate_answer("A prompt")


@patch("app.integrations.llm._get_client")
def test_generate_answer_rejects_empty_response(mock_get_client):
    mock_get_client.return_value = _client_with_answer("   ")

    with pytest.raises(GenerationError, match="empty response"):
        generate_answer("A prompt")


@patch("app.integrations.llm._get_client")
def test_generation_error_message_hides_provider_details(
    mock_get_client,
):
    mock_get_client.return_value.models.generate_content.side_effect = (
        RuntimeError("secret api key xyz")
    )

    with pytest.raises(GenerationError) as excinfo:
        generate_answer("A prompt")

    assert "secret" not in str(excinfo.value)
    assert "api key" not in str(excinfo.value)
