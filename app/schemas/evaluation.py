from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class ExpectedSource(BaseModel):
    """A ground-truth source expectation."""

    document_id: int
    page: Optional[int] = Field(default=None, ge=0)


class EvaluationCaseBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    question: str = Field(..., min_length=1, max_length=10000)


class EvaluationCaseCreate(EvaluationCaseBase):
    reference_answer: Optional[str] = Field(
        default=None, max_length=10000
    )
    required_facts: Optional[list[str]] = Field(
        default=None, max_length=100
    )
    expected_sources: Optional[list[ExpectedSource]] = Field(
        default=None, max_length=100
    )
    selected_document_ids: Optional[list[int]] = Field(
        default=None, max_length=100
    )


class EvaluationCaseUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    question: Optional[str] = Field(None, min_length=1, max_length=10000)
    reference_answer: Optional[str] = Field(None, max_length=10000)
    required_facts: Optional[list[str]] = Field(None, max_length=100)
    expected_sources: Optional[list[ExpectedSource]] = Field(None, max_length=100)
    selected_document_ids: Optional[list[int]] = Field(None, max_length=100)


class EvaluationCaseResponse(EvaluationCaseBase):
    id: int
    workspace_id: int
    reference_answer: Optional[str] = None
    required_facts: Optional[list[str]] = None
    expected_sources: Optional[list[dict]] = None
    selected_document_ids: Optional[list[int]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationRunResponse(BaseModel):
    id: int
    evaluation_case_id: int
    status: str
    answer: Optional[str] = None
    actual_sources: Optional[list[dict]] = None
    metrics: Optional[dict] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
