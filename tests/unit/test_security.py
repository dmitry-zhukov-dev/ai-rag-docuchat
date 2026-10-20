from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import security
from app.core.config import settings
from app.db.base import Base
from app.db.models.session import Session as SessionModel


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_create_session_returns_active_session(db_session):
    session = security.create_session(db_session)

    assert session.id
    assert len(session.id) >= 32
    assert security.is_session_active(session)


def test_get_session_by_id_round_trip(db_session):
    created = security.create_session(db_session)

    found = security.get_session_by_id(db_session, created.id)

    assert found is not None
    assert found.id == created.id


def test_get_session_by_id_rejects_unknown_id(db_session):
    assert security.get_session_by_id(db_session, "missing") is None


def test_expired_session_is_rejected(db_session):
    expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    session = SessionModel(id="expired", expires_at=expires_at)
    db_session.add(session)
    db_session.commit()

    assert security.get_session_by_id(db_session, "expired") is None


def test_get_session_id_from_cookie():
    class FakeRequest:
        def __init__(self, cookies):
            self.cookies = cookies

    request = FakeRequest(
        {settings.session_cookie_name: "abc123"}
    )

    assert security.get_session_id_from_cookie(request) == "abc123"

    assert (
        security.get_session_id_from_cookie(FakeRequest({})) is None
    )
    assert (
        security.get_session_id_from_cookie(
            FakeRequest({settings.session_cookie_name: "   "})
        )
        is None
    )


def test_require_workspace_access_denies_foreign_workspace(
    db_session,
):
    from app.db.models.workspace import Workspace

    other = security.create_session(db_session)
    workspace = Workspace(name="Mine", session_id=other.id)
    db_session.add(workspace)
    db_session.commit()

    session = security.create_session(db_session)

    with pytest.raises(HTTPException) as excinfo:
        security.require_workspace_access(
            db_session, session, workspace.id
        )

    assert excinfo.value.status_code == 404


def test_require_workspace_access_allows_owner(db_session):
    from app.db.models.workspace import Workspace

    session = security.create_session(db_session)
    workspace = Workspace(name="Mine", session_id=session.id)
    db_session.add(workspace)
    db_session.commit()

    owned = security.require_workspace_access(
        db_session, session, workspace.id
    )

    assert owned.id == workspace.id
