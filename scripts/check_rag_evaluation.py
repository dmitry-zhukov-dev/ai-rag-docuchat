
from uuid import uuid4

from qdrant_client import models

from app.rag.generation import answer_question
from app.rag.ingestion import ingest_document
from app.integrations.qdrant import (
    COLLECTION_NAME,
    get_qdrant_client,
)

DOCUMENT_PATH = "scripts/sample_document.txt"


def main() -> None:
    document_id = str(uuid4())

    try:
        chunks_count = ingest_document(
            file_path=DOCUMENT_PATH,
            document_id=document_id,
            workspace_id="smoke-test",
            filename=DOCUMENT_PATH,
        )
        print(f"Document indexed. Chunks: {chunks_count}")

        questions = [
            {
                "question": "What does RAG stand for?",
                "expected": "The answer is present in the document.",
            },
            {
                "question": "What is the capital of Japan?",
                "expected": "The answer is absent from the document.",
            },
        ]

        for item in questions:
            print(f"\nQuestion: {item['question']}")
            print(f"Check: {item['expected']}")

            answer = answer_question(
                question=item["question"],
                document_id=document_id,
            )

            print(f"Answer: {answer}")

    finally:
        try:
            client = get_qdrant_client()
            client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(
                                    value=document_id
                                ),
                            )
                        ]
                    )
                ),
                wait=True,
            )
            print("\nTemporary document data cleaned up.")
        except Exception as exc:
            print(
                "\nWarning: cleanup failed or timed out. "
                f"Check Qdrant manually. Details: {exc}"
            )


if __name__ == "__main__":
    main()
