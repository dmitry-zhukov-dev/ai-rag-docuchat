
from uuid import uuid4

from qdrant_client import models

from app.integrations import qdrant
from app.rag.generation import answer_question
from app.rag.ingestion import ingest_document


def main() -> None:
    document_id = f"rag-test-{uuid4()}"

    try:
        chunk_count = ingest_document(
            file_path="scripts/sample_document.txt",
            document_id=document_id,
            workspace_id="smoke-test",
            filename="sample_document.txt",
        )
        print(f"Document indexed. Chunks saved: {chunk_count}")

        answer = answer_question(
            question="What does RAG stand for?",
            workspace_id="smoke-test",
            document_id=document_id,
        )

        print("\nGemini answer:")
        print(answer)

        assert chunk_count > 0, "No chunks were created."
        assert answer.strip(), "The answer is empty."

        print("\nFull RAG pipeline works!")

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
