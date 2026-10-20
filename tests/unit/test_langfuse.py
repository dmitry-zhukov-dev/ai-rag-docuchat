from unittest.mock import MagicMock, patch

from app.integrations import langfuse
from app.integrations.langfuse import (
    LangfuseTracer,
    NullObservation,
)


def test_tracer_is_inactive_when_disabled(monkeypatch):
    monkeypatch.setattr(
        langfuse.settings, "langfuse_enabled", False
    )
    tracer = LangfuseTracer()

    assert tracer._get_client() is None


def test_trace_yields_noop_when_disabled(monkeypatch):
    monkeypatch.setattr(
        langfuse.settings, "langfuse_enabled", False
    )
    tracer = LangfuseTracer()

    with tracer.trace("answer_question") as observation:
        assert isinstance(observation, NullObservation)
        observation.update(output={"chunks": 1})
        observation.end()


def test_span_yields_noop_when_client_creation_fails(
    monkeypatch,
):
    monkeypatch.setattr(
        langfuse.settings, "langfuse_enabled", True
    )
    monkeypatch.setattr(
        langfuse.settings, "langfuse_public_key", "pk"
    )
    monkeypatch.setattr(
        langfuse.settings, "langfuse_secret_key", "sk"
    )

    def broken_import(name):
        raise ImportError("no langfuse")

    with patch.dict("sys.modules", {"langfuse": None}):
        tracer = LangfuseTracer()
        # Force a fresh resolution.
        tracer._resolved = False
        assert tracer._get_client() is None

    with tracer.span("retrieval") as observation:
        assert isinstance(observation, NullObservation)


def test_trace_and_span_use_the_client(monkeypatch):
    monkeypatch.setattr(
        langfuse.settings, "langfuse_enabled", True
    )
    monkeypatch.setattr(
        langfuse.settings, "langfuse_public_key", "pk"
    )
    monkeypatch.setattr(
        langfuse.settings, "langfuse_secret_key", "sk"
    )

    observation = MagicMock()
    observation.__enter__ = MagicMock(
        return_value=observation
    )
    observation.__exit__ = MagicMock(return_value=False)

    client = MagicMock()
    client.start_as_current_observation.return_value = (
        observation
    )

    tracer = LangfuseTracer()
    tracer._resolved = True
    tracer._client = client

    with tracer.trace("answer_question") as trace:
        assert trace is observation

    with tracer.span("retrieval") as span:
        assert span is observation

    assert (
        client.start_as_current_observation.call_count == 2
    )

    tracer.flush()
    client.flush.assert_called_once()


def test_missing_credentials_keep_tracing_inactive(
    monkeypatch,
):
    monkeypatch.setattr(
        langfuse.settings, "langfuse_enabled", True
    )
    monkeypatch.setattr(
        langfuse.settings, "langfuse_public_key", ""
    )
    monkeypatch.setattr(
        langfuse.settings, "langfuse_secret_key", ""
    )

    tracer = LangfuseTracer()

    assert tracer._get_client() is None
