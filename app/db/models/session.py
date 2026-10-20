from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Session(Base):
    """An anonymous user session.

    The identifier is a cryptographically random hex string
    that is only transmitted through a secure cookie. It is
    never logged and never returned in API responses.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    workspaces: Mapped[list["Workspace"]] = relationship(
        back_populates="session"
    )
