from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_db
from app.core import security
from app.core.config import settings
from app.db.models.session import Session as SessionModel

router = APIRouter()


def _set_session_cookie(response: Response, session_id: str) -> None:
    lifetime_seconds = settings.session_lifetime_days * 86400
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        httponly=settings.session_cookie_httponly,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        max_age=lifetime_seconds,
        expires=lifetime_seconds,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name, path="/"
    )


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session_route(
    response: Response, db: Session = Depends(get_db)
) -> dict[str, str]:
    """Start an anonymous session and set its cookie.

    The session identifier is only transmitted through the
    cookie; it is not returned in the response body.
    """
    session = security.create_session(db)
    _set_session_cookie(response, session.id)
    return {"status": "ok"}


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
def delete_session_route(
    response: Response,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
) -> None:
    """End the current session and clear its cookie."""
    security.delete_session(db, session.id)
    _clear_session_cookie(response)
    return None
