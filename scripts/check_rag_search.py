
from uuid import uuid4

from qdrant_client import models

from app.integrations import qdrant
from app.integrations.embeddings import embed_query, embed_texts
from app.rag.chunking import chunk_text
from app.rag.loaders import LoadedSegment


def main() -> None:
    document_id = f"rag-test-{uuid4()}"

    text = """
    Python is a popular programming language used for backend development.
    FastAPI is a Python framework for building web APIs.
    PostgreSQL is a relational database used to store structured data.
    Qdrant is a vector database used for semantic search.
    """

    try:
        chunks = chunk_text(
            [LoadedSegment(text=text, page=None)],
            chunk_size=100,
            chunk_overlap=20,
        )
        vectors = embed_texts([chunk.text for chunk in chunks])

        qdrant.create_collection()
        qdrant.save_chunks(
            document_id=document_id,
            workspace_id="smoke-test",
            filename="sample_document.txt",
            chunks=chunks,
            vectors=vectors,
        )

        question = "Which tool can find information by meaning using vectors?"
        query_vector = embed_query(question)

        results = qdrant.search_chunks(
            query_vector=query_vector,
            workspace_id="smoke-test",
            limit=3,
            document_id=document_id,
        )

        print(f"Question: {question}\n")
        for result in results:
            print(f"Score: {result['score']:.4f}")
            print(f"Text: {result['text']}\n")

        assert results, "No results returned."

    finally:
        client = qdrant.get_qdrant_client()
        if client.collection_exists(qdrant.COLLECTION_NAME):
            client.delete(
                collection_name=qdrant.COLLECTION_NAME,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=document_id),
                        )
                    ]
                ),
                wait=True,
            )


if __name__ == "__main__":
    main()
