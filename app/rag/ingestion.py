from app.integrations.embeddings import embed_texts
from app.integrations.qdrant import save_chunks
from app.rag.chunking import chunk_text
from app.rag.loaders import load_document


def ingest_document(
    file_path: str,
    document_id: str,
    workspace_id: str,
    filename: str,
) -> int:
    """Load, split, embed, and store a document. Return chunk count.

    The workspace identifier and original filename are stored with every
    chunk so that retrieval can filter by workspace and answers can be
    attributed to their source documents.
    """
    segments = load_document(file_path)
    chunks = chunk_text(segments)

    if not chunks:
        return 0

    chunk_texts = [chunk.text for chunk in chunks]
    vectors = embed_texts(chunk_texts)
    save_chunks(
        document_id=document_id,
        workspace_id=workspace_id,
        filename=filename,
        chunks=chunks,
        vectors=vectors,
    )

    return len(chunks)
