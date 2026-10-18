
import os
from functools import lru_cache

from dotenv import load_dotenv
from google import genai

MODEL_NAME = "gemini-3.8-flash"

load_dotenv()


@lru_cache(maxsize=1)
def _get_client() -> genai.Client:
    """Create and reuse the Gemini API client."""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Add it to the .env file."
        )

    return genai.Client(api_key=api_key)


def generate_answer(prompt: str) -> str:
    """Generate a text response using Gemini."""
    if not isinstance(prompt, str):
        raise TypeError("prompt must be a string.")

    if not prompt.strip():
        raise ValueError("prompt cannot be empty or whitespace.")

    response = _get_client().models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )

    answer = response.text

    if not answer or not answer.strip():
        raise RuntimeError("Gemini returned an empty response.")

    return answer.strip()
