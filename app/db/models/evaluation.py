from datetime import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, func, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    # Ground truth for deterministic metrics.
    reference_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_facts: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    expected_sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Documents the test case is restricted to; empty
    # or null means all ready documents in the workspace.
    selected_document_ids: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped["Workspace"] = relationship(back_populates="evaluation_cases")
    runs: Mapped[list["EvaluationRun"]] = relationship(
        back_populates="evaluation_case",
        cascade="all, delete-orphan",
    )

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_case_id: Mapped[int] = mapped_column(ForeignKey("evaluation_cases.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # The actual answer produced by the RAG pipeline.
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # The sources actually retrieved and used.
    actual_sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Diagnostic information when execution failed.
    error: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    evaluation_case: Mapped["EvaluationCase"] = relationship(back_populates="runs")
