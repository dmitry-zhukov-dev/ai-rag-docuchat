
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10000)
    limit: int = Field(default=5, ge=1, le=20)


class ChatResponse(BaseModel):
    conversation_id: int
    question: str
    answer: str
