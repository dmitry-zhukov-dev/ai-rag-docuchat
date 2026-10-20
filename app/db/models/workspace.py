from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # The anonymous session that owns this workspace.
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="workspaces")
    documents: Mapped[list["Document"]] = relationship(back_populates="workspace")
    conversations: Mapped[list["Conversation"]] = relationship(back_populates="workspace")
    evaluation_cases: Mapped[list["EvaluationCase"]] = relationship(back_populates="workspace")
