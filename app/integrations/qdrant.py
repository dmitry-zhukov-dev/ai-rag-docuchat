from functools import lru_cache
from uuid import NAMESPACE_DNS, uuid5

from qdrant_client import QdrantClient, models

from app.integrations.embeddings import EMBEDDING_DIMENSION
from app.core.config import settings
from app.rag.chunking import Chunk


COLLECTION_NAME = settings.qdrant_collection
QDRANT_URL = settings.qdrant_url

# Namespace for deterministic chunk point IDs. Deriving the point ID from
# the chunk identifier makes repeated indexing idempotent: re-indexing the
# same document overwrites the same points instead of creating duplicates.
CHUNK_POINT_NAMESPACE = uuid5(NAMESPACE_DNS, "docuchat-chunk-point")


def make_chunk_id(document_id: str, chunk_index: int) -> str:
    """Return a chunk identifier unique within the collection.

    The document identifier is part of the chunk identifier, so the chunk
    index alone is never relied upon for uniqueness.
    """
    return f"{document_id}:{chunk_index}"

# Namespace for deterministic chunk point IDs. Deriving the point ID from
# the chunk identifier makes repeated indexing idempotent: re-indexing the
# same document overwrites the same points instead of creating duplicates.
CHUNK_POINT_NAMESPACE = uuid5(NAMESPACE_DNS, "docuchat-chunk-point")


def make_chunk_id(document_id: str, chunk_index: int) -> str:
    """Return a chunk identifier unique within the collection.

    The document identifier is part of the chunk identifier, so the chunk
    index alone is never relied upon for uniqueness.
    """
    return f"{document_id}:{chunk_index}"


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
    *,
    document_id: str,
    workspace_id: str,
    filename: str,
    chunks: list[Chunk],
    vectors: list[list[float]],
) -> list[str]:
    """Save document chunks and their embeddings to Qdrant.

    Each point payload carries the metadata required for retrieval and
    source attribution: workspace_id, document_id, chunk_id, chunk_index,
    text, filename, and page (None for TXT documents).
    """
    if not isinstance(document_id, str) or not document_id.strip():
        raise ValueError("document_id cannot be empty.")

    if not isinstance(workspace_id, str) or not workspace_id.strip():
        raise ValueError("workspace_id cannot be empty.")

    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename cannot be empty.")

    if not isinstance(chunks, list) or not isinstance(vectors, list):
        raise TypeError("chunks and vectors must be lists.")

    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors must have the same length.")

    if any(not isinstance(chunk, Chunk) or not chunk.text.strip() for chunk in chunks):
        raise ValueError("chunks cannot contain empty or non-Chunk values.")

    if any(len(vector) != EMBEDDING_DIMENSION for vector in vectors):
        raise ValueError(
            f"Each vector must contain {EMBEDDING_DIMENSION} dimensions."
        )

    if not chunks:
        return []

    client = get_qdrant_client()
    create_collection()

    points = []
    point_ids = []

    for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
        chunk_id = make_chunk_id(document_id, index)
        point_id = str(uuid5(CHUNK_POINT_NAMESPACE, chunk_id))
        point_ids.append(point_id)

        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "workspace_id": workspace_id,
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": index,
                    "text": chunk.text,
                    "filename": filename,
                    "page": chunk.page,
                },
            )
        )

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
        wait=True,
    )

    return point_ids


def search_chunks(
    query_vector: list[float],
    workspace_id: str,
    limit: int = 5,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    """Find similar chunks within a workspace.

    The workspace filter is always applied on the Qdrant side, optionally
    combined with single-document or selected-document restrictions.
    """
    if len(query_vector) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"query_vector must contain {EMBEDDING_DIMENSION} dimensions."
        )

    if not isinstance(workspace_id, str) or not workspace_id.strip():
        raise ValueError("workspace_id cannot be empty.")

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

    # Every search is scoped to the calling workspace. The workspace
    # condition is combined with the requested document restrictions so
    # that chunks from other workspaces can never enter the results.
    workspace_condition = models.FieldCondition(
        key="workspace_id",
        match=models.MatchValue(value=workspace_id),
    )

    if document_ids is not None:
        query_filter = models.Filter(
            must=[workspace_condition],
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
                workspace_condition,
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            ]
        )
    else:
        query_filter = models.Filter(must=[workspace_condition])

    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    ).points

    return [
        {
            "workspace_id": point.payload.get("workspace_id"),
            "document_id": point.payload.get("document_id"),
            "chunk_id": point.payload.get("chunk_id"),
            "chunk_index": point.payload.get("chunk_index"),
            "filename": point.payload.get("filename"),
            "text": point.payload.get("text"),
            "page": point.payload.get("page"),
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
