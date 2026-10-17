from datetime import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, DateTime, func, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metrics: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    evaluation_case: Mapped["EvaluationCase"] = relationship(back_populates="runs")
