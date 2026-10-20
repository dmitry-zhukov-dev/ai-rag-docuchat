from typing import Optional

from pydantic import BaseModel, Field


class SourceResponse(BaseModel):
    """A verifiable source derived from a retrieved chunk."""

    document_id: str
    filename: str
    page: Optional[int] = Field(default=None, ge=0)
    chunk_id: str
    snippet: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10000)
    limit: int = Field(default=5, ge=1, le=20)
    # Omitted (None): all ready documents in the workspace
    # are searched. An explicitly empty list searches no
    # documents. The two cases are never conflated.
    document_ids: Optional[list[int]] = Field(
        default=None, max_length=100
    )


class ChatResponse(BaseModel):
    conversation_id: int
    question: str
    answer: str
    insufficient_context: bool
    sources: list[SourceResponse]
