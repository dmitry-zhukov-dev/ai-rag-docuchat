
from app.integrations.embeddings import embed_texts
from app.integrations.qdrant import save_chunks
from app.rag.chunking import chunk_text
from app.rag.loaders import load_document


def ingest_document(
    file_path: str,
    document_id: str,
) -> int:
    """Load, split, embed, and store a document. Return chunk count."""
    text = load_document(file_path)
    chunks = chunk_text(text)

    if not chunks:
        return 0

    vectors = embed_texts(chunks)
    save_chunks(
        document_id=document_id,
        chunks=chunks,
        vectors=vectors,
    )

    return len(chunks)
