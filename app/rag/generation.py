
from app.integrations.llm import generate_answer
from app.rag.prompting import build_prompt
from app.rag.retrieval import retrieve_chunks


def answer_question(
    question: str,
    limit: int = 5,
    document_id: str | None = None,
) -> str:
    """Answer a question using retrieved document context."""
    chunks = retrieve_chunks(
        question=question,
        limit=limit,
        document_id=document_id,
    )

    prompt = build_prompt(
        question=question,
        context_chunks=chunks,
    )

    return generate_answer(prompt)
