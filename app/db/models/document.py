
from datetime import datetime
from typing import Optional

from sqlalchemy import String, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        ForeignKey("workspaces.id"),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_format: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    num_pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    indexing_status: Mapped[str] = mapped_column(
        String(50),
        default="processing",
    )
    # Diagnostic information for failed indexing or
    # partial cleanup. Never contains secrets or full
    # document content.
    error_message: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    workspace: Mapped["Workspace"] = relationship(
        back_populates="documents",
    )
