
from app.integrations.embeddings import embed_query
from app.integrations.qdrant import search_chunks


def retrieve_chunks(
    question: str,
    limit: int = 5,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
) -> list[dict]:
    """Retrieve relevant document chunks for a question."""
    if not isinstance(question, str):
        raise TypeError("question must be a string.")

    if not question.strip():
        raise ValueError("question cannot be empty or whitespace.")

    query_vector = embed_query(question)

    return search_chunks(
        query_vector=query_vector,
        limit=limit,
        document_id=document_id,
        document_ids=document_ids,
    )
