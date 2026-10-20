
from uuid import uuid4

from qdrant_client import models

from app.integrations import qdrant
from app.rag.chunking import Chunk


def main() -> None:
    document_id = f"smoke-test-{uuid4()}"
    vector_a = [1.0] + [0.0] * 383
    vector_b = [0.0, 1.0] + [0.0] * 382

    try:
        qdrant.create_collection()
        print("1. Collection ready")

        qdrant.save_chunks(
            document_id=document_id,
            workspace_id="smoke-test",
            filename="sample_document.txt",
            chunks=[
                Chunk(text="Python is a programming language.", page=None),
                Chunk(text="The weather is sunny today.", page=None),
            ],
            vectors=[vector_a, vector_b],
        )
        print("2. Chunks saved")

        results = qdrant.search_chunks(
            query_vector=vector_a,
            workspace_id="smoke-test",
            limit=2,
            document_id=document_id,
        )

        assert results, "Search returned no results."
        assert results[0]["text"] == "Python is a programming language."

        print("3. Search returned the expected chunk")
        print(f"   Text: {results[0]['text']}")
        print(f"   Score: {results[0]['score']:.4f}")
        print("\nQdrant integration works!")

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
