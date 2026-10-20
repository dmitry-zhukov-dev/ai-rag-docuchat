import logging
from dataclasses import dataclass

from app.integrations.langfuse import tracer
from app.integrations.llm import generate_answer_detailed
from app.rag.prompting import build_prompt
from app.rag.retrieval import retrieve_chunks, verify_chunks

logger = logging.getLogger(__name__)

# Upper bound for the source snippet stored with an answer.
SNIPPET_MAX_LENGTH = 300


@dataclass(frozen=True)
class RAGAnswer:
    """Structured result of RAG answer generation.

    The answer text, the insufficient-context status, and the
    machine-verifiable sources are separate fields so that
    consumers never have to parse the answer text.
    """

    answer: str
    insufficient_context: bool
    sources: list[dict]
    chunks: list[dict]


def _build_sources(chunks: list[dict]) -> list[dict]:
    """Derive verifiable sources from actually retrieved chunks."""
    sources = []

    for chunk in chunks:
        text = chunk.get("text")
        snippet = text.strip() if isinstance(text, str) else ""

        if len(snippet) > SNIPPET_MAX_LENGTH:
            snippet = snippet[:SNIPPET_MAX_LENGTH].rstrip() + "…"

        sources.append(
            {
                "document_id": chunk.get("document_id"),
                "filename": chunk.get("filename"),
                "page": chunk.get("page"),
                "chunk_id": chunk.get("chunk_id"),
                "snippet": snippet,
            }
        )

    return sources


def answer_question(
    question: str,
    workspace_id: str,
    limit: int = 5,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
    history: list[dict] | None = None,
    accessible_document_ids: set[str] | None = None,
) -> RAGAnswer:
    """Answer a question using retrieved context and chat history.

    Returns a structured RAGAnswer. When no verified chunks are
    retrieved, the generation provider is not called and the
    result reports insufficient context instead of inventing an
    answer.

    Retrieval and generation are traced as separate steps when
    the optional Langfuse integration is enabled; tracing never
    affects the result.
    """
    with tracer.trace(
        "answer_question",
        metadata={"workspace_id": workspace_id},
    ):
        with tracer.span("retrieval") as retrieval_step:
            chunks = retrieve_chunks(
                question=question,
                workspace_id=workspace_id,
                limit=limit,
                document_id=document_id,
                document_ids=document_ids,
            )

            if accessible_document_ids is not None:
                chunks, diagnostics = verify_chunks(
                    chunks, accessible_document_ids
                )

                for diagnostic in diagnostics:
                    logger.warning(
                        "Dropped retrieved chunk inconsistent"
                        " with relational data: %s",
                        diagnostic,
                    )

            retrieval_step.update(
                output={
                    "retrieved_chunk_count": len(chunks),
                }
            )

        if not chunks:
            return RAGAnswer(
                answer="",
                insufficient_context=True,
                sources=[],
                chunks=[],
            )

        prompt = build_prompt(
            question=question,
            context_chunks=chunks,
            history=history,
        )

        with tracer.span("generation") as generation_step:
            answer, usage = generate_answer_detailed(prompt)

            generation_step.update(
                output={"answer_length": len(answer)},
                usage_details=usage,
            )

        return RAGAnswer(
            answer=answer,
            insufficient_context=False,
            sources=_build_sources(chunks),
            chunks=chunks,
        )
