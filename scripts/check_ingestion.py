
from uuid import uuid4

from app.integrations import qdrant
from app.integrations.embeddings import embed_query
from app.rag.ingestion import ingest_document


def main() -> None:
    document_id = f"ingestion-test-{uuid4()}"

    try:
        chunk_count = ingest_document(
            file_path="scripts/sample_document.txt",
            document_id=document_id,
        )

        print(f"Document indexed. Chunks saved: {chunk_count}")

        results = qdrant.search_chunks(
            query_vector=embed_query(
                "How does DocuChat search for information?"
            ),
            limit=3,
            document_id=document_id,
        )

        print("\nSearch results:")
        for result in results:
            print(f"- Score: {result['score']:.4f}")
            print(f"  Text: {result['text']}")

        assert chunk_count > 0, "No chunks were created."
        assert results, "No search results were returned."

        print("\nIngestion pipeline works!")

    finally:
        client = qdrant.get_qdrant_client()

        if client.collection_exists(qdrant.COLLECTION_NAME):
            from qdrant_client import models

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
