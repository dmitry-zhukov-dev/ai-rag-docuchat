
import logging
import os
from functools import lru_cache
from typing import Any, Optional

from dotenv import load_dotenv
from google import genai

from app.core.config import settings

logger = logging.getLogger(__name__)

MODEL_NAME = settings.gemini_model

load_dotenv()


class GenerationError(Exception):
    """Raised when the generation provider fails.

    The message is safe to return to API clients: it never
    contains provider error details, keys, or prompt content.
    """


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    """Create and reuse the Gemini API client."""
    api_key = os.getenv("GEMINI_API_KEY") or settings.gemini_api_key

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to the .env file."
        )

    return genai.Client(api_key=api_key)


def _extract_usage(response: Any) -> Optional[dict]:
    """Extract token usage from a provider response."""
    usage_metadata = getattr(response, "usage_metadata", None)

    if usage_metadata is None:
        return None

    usage = {
        key: getattr(usage_metadata, key, None)
        for key in (
            "prompt_token_count",
            "candidates_token_count",
            "total_token_count",
        )
    }

    if all(value is None for value in usage.values()):
        return None

    return usage


def generate_answer_detailed(prompt: str) -> tuple[str, Optional[dict]]:
    """Generate a text response and report token usage.

    Provider timeouts, errors, and rate limits are translated
    into GenerationError so that callers receive a single,
    sanitized application error instead of provider details.
    """
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string.")

    if not prompt.strip():
        raise ValueError("prompt cannot be empty or whitespace.")

    try:
        response = _get_client().models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
        )
        answer = response.text
        usage = _extract_usage(response)
    except GenerationError:
        raise
    except Exception as exc:
        # Log the provider failure class for diagnostics without
        # leaking provider messages, keys, or prompt content.
        logger.error(
            "Gemini generation failed: %s", type(exc).__name__
        )
        raise GenerationError(
            "The answer could not be generated because the "
            "generation provider failed."
        ) from exc

    if not answer or not answer.strip():
        raise GenerationError(
            "The answer could not be generated because the "
            "generation provider returned an empty response."
        )

    return answer.strip(), usage


def generate_answer(prompt: str) -> str:
    """Generate a text response using Gemini."""
    answer, _ = generate_answer_detailed(prompt)
    return answer
