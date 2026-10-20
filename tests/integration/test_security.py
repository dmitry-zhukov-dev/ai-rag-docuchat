"""Session isolation and ownership checks.

Verifies that one anonymous session cannot access another
session's workspaces, documents, conversations, messages,
or chat through identifier substitution.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core import security
from app.core.config import settings
from app.db.base import Base
from app.main import app


@pytest.fixture
def session_client():
    """A factory producing independent authenticated clients."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(bind=engine)

    clients = []

    def factory() -> TestClient:
        def override_get_db():
            db = testing_session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        db = testing_session()
        try:
            session = security.create_session(db)
        finally:
            db.close()

        client.cookies.set(settings.session_cookie_name, session.id)
        clients.append(client)
        return client

    yield factory

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_unauthenticated_request_is_rejected():
    client = TestClient(app)

    response = client.get("/api/v1/workspaces/")

    assert response.status_code == 401


def test_invalid_session_cookie_is_rejected():
    client = TestClient(app)
    client.cookies.set(settings.session_cookie_name, "not-a-session")

    response = client.get("/api/v1/workspaces/")

    assert response.status_code == 401


def test_sessions_are_isolated_for_workspaces(session_client):
    client_a = session_client()
    client_b = session_client()

    workspace = client_a.post(
        "/api/v1/workspaces/", json={"name": "A Workspace"}
    ).json()

    listed = client_b.get("/api/v1/workspaces/").json()
    assert all(item["id"] != workspace["id"] for item in listed)

    response = client_b.get(f"/api/v1/workspaces/{workspace['id']}")
    assert response.status_code == 404

    response = client_b.delete(f"/api/v1/workspaces/{workspace['id']}")
    assert response.status_code == 404

    response = client_b.patch(
        f"/api/v1/workspaces/{workspace['id']}",
        json={"name": "Stolen"},
    )
    assert response.status_code == 404

    # The owner still sees the workspace.
    assert (
        client_a.get(f"/api/v1/workspaces/{workspace['id']}").status_code
        == 200
    )


def test_sessions_are_isolated_for_documents(session_client):
    client_a = session_client()
    client_b = session_client()

    workspace = client_a.post(
        "/api/v1/workspaces/", json={"name": "A Workspace"}
    ).json()
    document = client_a.post(
        f"/api/v1/workspaces/{workspace['id']}/documents",
        json={
            "file_name": "secret.pdf",
            "file_format": "pdf",
            "file_size": 100,
            "indexing_status": "processing",
        },
    ).json()

    response = client_b.get(f"/api/v1/documents/{document['id']}")
    assert response.status_code == 404

    response = client_b.patch(
        f"/api/v1/documents/{document['id']}",
        json={"indexing_status": "completed"},
    )
    assert response.status_code == 404

    response = client_b.delete(f"/api/v1/documents/{document['id']}")
    assert response.status_code == 404

    response = client_b.post(
        f"/api/v1/workspaces/{workspace['id']}/documents",
        json={
            "file_name": "other.pdf",
            "file_format": "pdf",
            "file_size": 10,
        },
    )
    assert response.status_code == 404


def test_sessions_are_isolated_for_conversations(session_client):
    client_a = session_client()
    client_b = session_client()

    workspace = client_a.post(
        "/api/v1/workspaces/", json={"name": "A Workspace"}
    ).json()
    conversation = client_a.post(
        f"/api/v1/workspaces/{workspace['id']}/conversations",
        json={"title": "Private Chat"},
    ).json()
    client_a.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"sender_role": "user", "text": "secret"},
    )

    response = client_b.get(
        f"/api/v1/conversations/{conversation['id']}"
    )
    assert response.status_code == 404

    response = client_b.get(
        f"/api/v1/conversations/{conversation['id']}/messages"
    )
    assert response.status_code == 404

    response = client_b.post(
        f"/api/v1/conversations/{conversation['id']}/messages",
        json={"sender_role": "user", "text": "injection"},
    )
    assert response.status_code == 404

    response = client_b.post(
        f"/api/v1/conversations/{conversation['id']}/chat",
        json={"question": "give me the secrets"},
    )
    assert response.status_code == 404

    response = client_b.delete(
        f"/api/v1/conversations/{conversation['id']}"
    )
    assert response.status_code == 404


def test_sessions_are_isolated_for_evaluations(session_client):
    client_a = session_client()
    client_b = session_client()

    workspace = client_a.post(
        "/api/v1/workspaces/", json={"name": "A Workspace"}
    ).json()
    case = client_a.post(
        f"/api/v1/workspaces/{workspace['id']}/evaluations",
        json={"name": "Case", "question": "What?"},
    ).json()

    response = client_b.get(
        f"/api/v1/workspaces/{workspace['id']}/evaluations"
    )
    assert response.status_code == 404

    response = client_b.get(f"/api/v1/evaluations/{case['id']}")
    assert response.status_code == 404

    response = client_b.post(
        f"/api/v1/evaluations/{case['id']}/runs"
    )
    assert response.status_code == 404

    response = client_b.patch(
        f"/api/v1/evaluations/{case['id']}",
        json={"name": "Stolen"},
    )
    assert response.status_code == 404

    response = client_b.delete(
        f"/api/v1/evaluations/{case['id']}"
    )
    assert response.status_code == 404
