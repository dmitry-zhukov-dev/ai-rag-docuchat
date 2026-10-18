
from functools import lru_cache

from sentence_transformers import SentenceTransformer


MODEL_NAME = "intfloat/multilingual-e5-small"
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it."""
    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> list[float]:
    """Convert a document passage into a normalized embedding."""
    if not isinstance(text, str):
        raise TypeError("text must be a string.")
    if not text.strip():
        raise ValueError("text cannot be empty or whitespace.")

    model = _get_model()
    vector = model.encode(
        f"passage: {text}",
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return vector.tolist()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Convert multiple document passages into embeddings."""
    if not isinstance(texts, list):
        raise TypeError("texts must be a list of strings.")
    if any(not isinstance(text, str) for text in texts):
        raise TypeError("every item in texts must be a string.")
    if any(not text.strip() for text in texts):
        raise ValueError("texts cannot contain empty or whitespace strings.")
    if not texts:
        return []

    model = _get_model()
    vectors = model.encode(
        [f"passage: {text}" for text in texts],
        normalize_embeddings=True,
        convert_to_numpy=True,
        batch_size=32,
    )

    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    """Convert a search query into an embedding."""
    if not isinstance(text, str):
        raise TypeError("text must be a string.")
    if not text.strip():
        raise ValueError("text cannot be empty or whitespace.")

    model = _get_model()
    vector = model.encode(
        f"query: {text}",
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return vector.tolist()
