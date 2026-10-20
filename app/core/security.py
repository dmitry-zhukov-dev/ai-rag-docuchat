"""Shared session and authorization mechanisms.

Every route obtains the anonymous session through the
``get_current_session`` dependency and verifies object
ownership with the ``require_*_access`` helpers. A
client-supplied object identifier is never treated as proof
of ownership: every check traverses the object back to the
session that created it.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.conversation import Conversation
from app.db.models.document import Document
from app.db.models.evaluation import EvaluationCase, EvaluationRun
from app.db.models.session import Session as SessionModel
from app.db.models.workspace import Workspace
from app.repositories.conversation import ConversationRepository
from app.repositories.document import DocumentRepository
from app.repositories.evaluation_case import EvaluationCaseRepository
from app.repositories.evaluation_run import EvaluationRunRepository
from app.repositories.session import SessionRepository
from app.repositories.workspace import WorkspaceRepository

logger = logging.getLogger(__name__)

session_repo = SessionRepository()
workspace_repo = WorkspaceRepository()
document_repo = DocumentRepository()
conversation_repo = ConversationRepository()
evaluation_case_repo = EvaluationCaseRepository()
evaluation_run_repo = EvaluationRunRepository()


def create_session(db: Session) -> SessionModel:
    """Create a new anonymous session with a random identifier."""
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.session_lifetime_days
    )
    return session_repo.create(
        db, session_id=uuid4().hex, expires_at=expires_at
    )


def delete_session(db: Session, session_id: str) -> bool:
    """Delete a session (logout)."""
    return session_repo.delete(db, session_id=session_id)


def is_session_active(session: SessionModel) -> bool:
    """Return True while the session has not expired."""
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at > datetime.now(timezone.utc)


def get_session_by_id(
    db: Session, session_id: str
) -> Optional[SessionModel]:
    """Return the session if it exists and has not expired."""
    session = session_repo.get(db, session_id)

    if session is None:
        return None

    if not is_session_active(session):
        session_repo.delete(db, session_id=session_id)
        return None

    return session


def get_session_id_from_cookie(request: Request) -> Optional[str]:
    """Read the session identifier from the request cookie."""
    value = request.cookies.get(settings.session_cookie_name)

    if not isinstance(value, str) or not value.strip():
        return None

    return value.strip()


def get_current_session(
    db: Session, request: Request
) -> SessionModel:
    """Resolve the current session from the request cookie.

    Raises 401 when the cookie is missing, unknown, or expired.
    """
    session_id = get_session_id_from_cookie(request)

    if session_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A session is required.",
        )

    session = get_session_by_id(db, session_id)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The session is missing or expired.",
        )

    return session


def _owned_by_session(workspace: Optional[Workspace], session_id: str) -> bool:
    return (
        workspace is not None
        and workspace.session_id == session_id
    )


def require_workspace_access(
    db: Session, session: SessionModel, workspace_id: int
) -> Workspace:
    """Verify that the workspace belongs to the session."""
    workspace = workspace_repo.get(db, workspace_id)

    if not _owned_by_session(workspace, session.id):
        # 404 for both missing and foreign workspaces so that
        # existence is not leaked.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found.",
        )

    return workspace


def require_document_access(
    db: Session, session: SessionModel, document_id: int
) -> Document:
    """Verify that the document belongs to the session."""
    document = document_repo.get(db, document_id)

    if document is None or not _owned_by_session(
        document.workspace, session.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        )

    return document


def require_conversation_access(
    db: Session, session: SessionModel, conversation_id: int
) -> Conversation:
    """Verify that the conversation belongs to the session."""
    conversation = conversation_repo.get(db, conversation_id)

    if conversation is None or not _owned_by_session(
        conversation.workspace, session.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    return conversation


def require_evaluation_case_access(
    db: Session, session: SessionModel, case_id: int
) -> EvaluationCase:
    """Verify that the evaluation case belongs to the session."""
    case = evaluation_case_repo.get(db, case_id)

    if case is None or not _owned_by_session(
        case.workspace, session.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation case not found.",
        )

    return case


def require_evaluation_run_access(
    db: Session, session: SessionModel, run_id: int
) -> EvaluationRun:
    """Verify that the evaluation run belongs to the session."""
    run = evaluation_run_repo.get(db, run_id)

    if run is None or not _owned_by_session(
        run.evaluation_case.workspace, session.id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation run not found.",
        )

    return run
