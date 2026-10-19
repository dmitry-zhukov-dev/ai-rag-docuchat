from unittest.mock import MagicMock, patch

import pytest
from qdrant_client import models

from app.integrations import qdrant
from app.rag.chunking import Chunk


@pytest.fixture
def mock_client():
    with patch(
        "app.integrations.qdrant.get_qdrant_client"
    ) as mock_get_client:
        client = MagicMock()
        mock_get_client.return_value = client
        yield client


def test_create_collection_creates_missing_collection(mock_client):
    mock_client.collection_exists.return_value = False

    qdrant.create_collection()

    mock_client.create_collection.assert_called_once_with(
        collection_name=qdrant.COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=384,
            distance=models.Distance.COSINE,
        ),
    )


def test_create_collection_does_not_recreate_existing_collection(
    mock_client,
):
    mock_client.collection_exists.return_value = True

    qdrant.create_collection()

    mock_client.create_collection.assert_not_called()


def test_save_chunks_stores_text_and_vectors(mock_client):
    mock_client.collection_exists.return_value = True

    chunks = [
        Chunk(text="First chunk", page=1),
        Chunk(text="Second chunk", page=None),
    ]
    vectors = [[0.1] * 384, [0.2] * 384]

    point_ids = qdrant.save_chunks("doc-1", chunks, vectors)

    assert len(point_ids) == 2
    assert len(set(point_ids)) == 2

    mock_client.upsert.assert_called_once()
    call = mock_client.upsert.call_args.kwargs

    assert call["collection_name"] == qdrant.COLLECTION_NAME
    assert call["wait"] is True

    points = call["points"]
    assert len(points) == 2
    assert points[0].payload == {
        "document_id": "doc-1",
        "chunk_index": 0,
        "text": "First chunk",
        "page": 1,
    }
    assert points[1].payload == {
        "document_id": "doc-1",
        "chunk_index": 1,
        "text": "Second chunk",
        "page": None,
    }


def test_save_chunks_rejects_empty_document_id(mock_client):
    with pytest.raises(ValueError, match="document_id"):
        qdrant.save_chunks("", [Chunk(text="chunk", page=1)], [[0.1] * 384])

    mock_client.upsert.assert_not_called()


def test_save_chunks_rejects_different_list_lengths(mock_client):
    with pytest.raises(ValueError, match="same length"):
        qdrant.save_chunks("doc-1", [Chunk(text="chunk", page=1)], [])

    mock_client.upsert.assert_not_called()


def test_save_chunks_rejects_wrong_vector_dimension(mock_client):
    with pytest.raises(ValueError, match="dimensions"):
        qdrant.save_chunks("doc-1", [Chunk(text="chunk", page=1)], [[0.1, 0.2]])

    mock_client.upsert.assert_not_called()


def test_save_chunks_returns_empty_list_for_no_chunks(mock_client):
    result = qdrant.save_chunks("doc-1", [], [])

    assert result == []
    mock_client.upsert.assert_not_called()


def test_search_chunks_returns_empty_if_collection_missing(mock_client):
    mock_client.collection_exists.return_value = False

    result = qdrant.search_chunks([0.1] * 384)

    assert result == []
    mock_client.query_points.assert_not_called()


def test_search_chunks_returns_results(mock_client):
    mock_client.collection_exists.return_value = True
    mock_client.query_points.return_value.points = [
        MagicMock(
            payload={
                "document_id": "doc-1",
                "chunk_index": 0,
                "text": "Relevant text",
                "page": 2,
            },
            score=0.95,
        )
    ]

    result = qdrant.search_chunks([0.1] * 384, limit=3)

    assert result == [
        {
            "document_id": "doc-1",
            "chunk_index": 0,
            "text": "Relevant text",
            "page": 2,
            "score": 0.95,
        }
    ]

    call = mock_client.query_points.call_args.kwargs
    assert call["collection_name"] == qdrant.COLLECTION_NAME
    assert call["limit"] == 3
    assert call["with_payload"] is True
    assert call["query_filter"] is None


def test_search_chunks_filters_by_document_id(mock_client):
    mock_client.collection_exists.return_value = True
    mock_client.query_points.return_value.points = []

    qdrant.search_chunks([0.1] * 384, document_id="doc-1")

    query_filter = mock_client.query_points.call_args.kwargs["query_filter"]

    assert query_filter.must[0].key == "document_id"
    assert query_filter.must[0].match.value == "doc-1"


@pytest.mark.parametrize("limit", [0, -1])
def test_search_chunks_rejects_invalid_limit(mock_client, limit):
    with pytest.raises(ValueError, match="limit"):
        qdrant.search_chunks([0.1] * 384, limit=limit)

    mock_client.query_points.assert_not_called()
