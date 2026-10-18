
from app.integrations.llm import generate_answer
from app.rag.prompting import build_prompt
from app.rag.retrieval import retrieve_chunks


def answer_question(
    question: str,
    limit: int = 5,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    history: list[dict] | None = None,
) -> str:
    """Answer a question using retrieved document context and chat history."""
    chunks = retrieve_chunks(
        question=question,
        limit=limit,
        document_id=document_id,
        document_ids=document_ids,
    )

    prompt = build_prompt(
        question=question,
        context_chunks=chunks,
        history=history,
    )

    return generate_answer(prompt)
