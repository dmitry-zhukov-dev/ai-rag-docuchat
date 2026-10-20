"""Optional Langfuse tracing for the RAG pipeline.

The integration is disabled by default and must never
break the core RAG workflow: every entry point is
guarded, and any failure reduces tracing to a no-op.

Privacy baseline (canonical plan section 10.4):
telemetry contains operation names, durations,
statuses, counts, and workspace identifiers only.
Question text, document text, answers, snippets,
API keys, cookies, and tokens are NOT transmitted.
Content telemetry would require a separate, explicit
opt-in and is not part of the MVP.
"""

import logging
from contextlib import contextmanager
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class NullObservation:
    """No-op stand-in used when tracing is inactive."""

    def update(self, *args: Any, **kwargs: Any) -> None:
        pass

    def end(self, *args: Any, **kwargs: Any) -> None:
        pass


class LangfuseTracer:
    """Guarded access to the Langfuse observations API.

    The client is resolved once from the configured
    settings. When the integration is disabled or the
    SDK is unavailable, all observations become no-ops.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._resolved = False

    def _get_client(self) -> Any:
        if self._resolved:
            return self._client
        self._resolved = True

        if not settings.langfuse_enabled:
            return None

        if not settings.langfuse_public_key or not (
            settings.langfuse_secret_key
        ):
            logger.warning(
                "Langfuse is enabled but credentials are"
                " missing; tracing stays inactive."
            )
            return None

        try:
            from langfuse import Langfuse

            self._client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
        except Exception as exc:
            logger.warning(
                "Langfuse is unavailable: %s",
                type(exc).__name__,
            )
            self._client = None

        return self._client

    def _start(
        self,
        as_type: str,
        name: str,
        metadata: Optional[dict],
    ) -> Any:
        client = self._get_client()

        if client is None:
            return None

        try:
            return client.start_as_current_observation(
                as_type=as_type,
                name=name,
                metadata=metadata or {},
            )
        except Exception as exc:
            logger.warning(
                "Langfuse observation could not be"
                " started: %s",
                type(exc).__name__,
            )
            return None

    @contextmanager
    def trace(
        self,
        name: str,
        metadata: Optional[dict] = None,
    ):
        """Open a trace-level observation."""
        context = self._start("trace", name, metadata)

        if context is None:
            yield NullObservation()
            return

        with context as observation:
            yield observation

    @contextmanager
    def span(
        self,
        name: str,
        metadata: Optional[dict] = None,
    ):
        """Open a nested span observation."""
        context = self._start("span", name, metadata)

        if context is None:
            yield NullObservation()
            return

        with context as observation:
            yield observation

    def flush(self) -> None:
        """Flush buffered events (short-lived processes)."""
        client = self._get_client()

        if client is None:
            return

        try:
            client.flush()
        except Exception as exc:
            logger.warning(
                "Langfuse flush failed: %s",
                type(exc).__name__,
            )


tracer = LangfuseTracer()
