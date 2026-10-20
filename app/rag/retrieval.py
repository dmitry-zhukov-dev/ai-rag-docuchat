
from app.integrations.embeddings import embed_query
from app.integrations.qdrant import search_chunks


def retrieve_chunks(
    question: str,
    workspace_id: str,
    limit: int = 5,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    """Retrieve relevant document chunks for a question within a workspace.

    The workspace identifier is passed to the vector search so that the
    workspace restriction is applied on the Qdrant side, never only by
    filtering results after retrieval.
    """
    if not isinstance(question, str):
        raise TypeError("question must be a string.")

    if not question.strip():
        raise ValueError("question cannot be empty or whitespace.")

    if not isinstance(workspace_id, str) or not workspace_id.strip():
        raise ValueError("workspace_id cannot be empty.")

    query_vector = embed_query(question)

    return search_chunks(
        query_vector=query_vector,
        workspace_id=workspace_id,
        limit=limit,
        document_id=document_id,
        document_ids=document_ids,
    )


def verify_chunks(
    chunks: list[dict],
    accessible_document_ids: set[str],
) -> tuple[list[dict], list[dict]]:
    """Verify retrieved chunks against application data.

    The existence of a Qdrant point does not prove that its
    document still exists, is ready, or belongs to the current
    workspace. Chunks that fail verification are dropped from the
    generation context and reported as diagnostics.

    Args:
        chunks: Retrieved chunks as returned by the vector search.
        accessible_document_ids: Identifiers of documents that
            exist, are ready, and are accessible in the current
            workspace.

    Returns:
        A tuple of (verified chunks, diagnostics). Each diagnostic
        records the chunk identifier, the document identifier, and
        the reason the chunk was dropped.
    """
    if not isinstance(chunks, list):
        raise TypeError("chunks must be a list.")

    if not isinstance(accessible_document_ids, (set, frozenset)):
        raise TypeError("accessible_document_ids must be a set of strings.")

    verified: list[dict] = []
    diagnostics: list[dict] = []

    for chunk in chunks:
        if not isinstance(chunk, dict):
            raise TypeError("each chunk must be a dictionary.")

        document_id = chunk.get("document_id")
        chunk_id = chunk.get("chunk_id")

        if not isinstance(document_id, str) or not document_id.strip():
            diagnostics.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "reason": "missing_document_id",
                }
            )
            continue

        if document_id not in accessible_document_ids:
            diagnostics.append(
                {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "reason": "document_not_accessible",
                }
            )
            continue

        verified.append(chunk)

    return verified, diagnostics
