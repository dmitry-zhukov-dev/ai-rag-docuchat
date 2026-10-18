
import numpy as np
import pytest

from app.integrations import embeddings


class FakeModel:
    def encode(
        self,
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        batch_size=None,
    ):
        if isinstance(texts, str):
            return np.ones(384, dtype=np.float32) / np.sqrt(384)

        return np.ones((len(texts), 384), dtype=np.float32) / np.sqrt(384)


@pytest.fixture
def fake_model(monkeypatch):
    monkeypatch.setattr(embeddings, "_get_model", lambda: FakeModel())


def test_embed_text_returns_384_values(fake_model):
    vector = embeddings.embed_text("Тестовый документ")

    assert len(vector) == 384
    assert all(isinstance(value, float) for value in vector)


def test_embed_text_rejects_empty_text():
    with pytest.raises(ValueError):
        embeddings.embed_text("   ")


def test_embed_text_rejects_non_string():
    with pytest.raises(TypeError):
        embeddings.embed_text(123)


def test_embed_texts_returns_one_vector_per_text(fake_model):
    vectors = embeddings.embed_texts(["Первый текст", "Второй текст"])

    assert len(vectors) == 2
    assert all(len(vector) == 384 for vector in vectors)


def test_embed_texts_returns_empty_list_for_empty_input(fake_model):
    assert embeddings.embed_texts([]) == []


def test_embed_texts_rejects_empty_items():
    with pytest.raises(ValueError):
        embeddings.embed_texts(["Нормальный текст", " "])


def test_embed_query_returns_384_values(fake_model):
    vector = embeddings.embed_query("Что написано в документе?")

    assert len(vector) == 384


def test_embed_query_rejects_empty_text():
    with pytest.raises(ValueError):
        embeddings.embed_query("")
