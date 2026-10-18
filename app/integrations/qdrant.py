
from functools import lru_cache
from uuid import uuid4

from qdrant_client import QdrantClient, models

from app.integrations.embeddings import EMBEDDING_DIMENSION


COLLECTION_NAME = "documents"
QDRANT_URL = "http://localhost:6333"


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    """Create and reuse the Qdrant client."""
    return QdrantClient(url=QDRANT_URL)


def create_collection() -> None:
    """Create the documents collection if it does not exist."""
    client = get_qdrant_client()

    if client.collection_exists(COLLECTION_NAME):
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=EMBEDDING_DIMENSION,
            distance=models.Distance.COSINE,
        ),
    )


def save_chunks(
    document_id: str,
    chunks: list[str],
    vectors: list[list[float]],
) -> list[str]:
    """Save document chunks and their embeddings to Qdrant."""
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id cannot be empty.")

    if not isinstance(chunks, list) or not isinstance(vectors, list):
        raise TypeError("chunks and vectors must be lists.")

    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors must have the same length.")

    if any(not isinstance(chunk, str) or not chunk.strip() for chunk in chunks):
        raise ValueError("chunks cannot contain empty or non-string values.")

    if any(len(vector) != EMBEDDING_DIMENSION for vector in vectors):
        raise ValueError(
            f"Each vector must contain {EMBEDDING_DIMENSION} dimensions."
        )

    if not chunks:
        return []

    client = get_qdrant_client()
    create_collection()

    point_ids = [str(uuid4()) for _ in chunks]

    points = [
        models.PointStruct(
            id=point_id,
            vector=vector,
            payload={
                "document_id": document_id,
                "chunk_index": index,
                "text": chunk,
            },
        )
        for index, (point_id, chunk, vector) in enumerate(
            zip(point_ids, chunks, vectors, strict=True)
        )
    ]

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )

    return point_ids


def search_chunks(
    query_vector: list[float],
    limit: int = 5,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    """Find similar chunks, optionally restricted to specific documents."""
    if len(query_vector) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"query_vector must contain {EMBEDDING_DIMENSION} dimensions."
        )

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer.")

    if limit <= 0:
        raise ValueError("limit must be greater than zero.")

    if document_ids is not None:
        if not isinstance(document_ids, list):
            raise TypeError("document_ids must be a list.")

        if any(not isinstance(item, str) or not item.strip() for item in document_ids):
            raise ValueError("document_ids cannot contain empty or non-string values.")

        # An explicitly empty list means there are no allowed documents.
        if not document_ids:
            return []

    client = get_qdrant_client()

    if not client.collection_exists(COLLECTION_NAME):
        return []

    query_filter = None

    if document_ids is not None:
        query_filter = models.Filter(
            should=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=doc_id),
                )
                for doc_id in document_ids
            ],
            min_should=models.MinShould(
                conditions=1,
            ),
        )
    elif document_id is not None:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            ]
        )

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    ).points

    return [
        {
            "document_id": point.payload.get("document_id"),
            "chunk_index": point.payload.get("chunk_index"),
            "text": point.payload.get("text"),
            "score": point.score,
        }
        for point in results
    ]


def delete_document_chunks(document_id: str) -> None:
    """Delete all indexed chunks belonging to a document."""
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id cannot be empty.")

    client = get_qdrant_client()

    if not client.collection_exists(COLLECTION_NAME):
        return

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    )
                ]
            )
        ),
        wait=True,
    )
