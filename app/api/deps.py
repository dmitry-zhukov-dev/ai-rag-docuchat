from typing import Generator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core import security
from app.core.security import SessionModel
from app.db.session import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_session(
    db: Session = Depends(get_db),
    request: Request = None,
) -> SessionModel:
    """Resolve the anonymous session from the cookie."""
    return security.get_current_session(db, request)
