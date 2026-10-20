from fastapi.testclient import TestClient

from app.core.config import settings


def test_create_session_sets_cookie(client: TestClient):
    response = client.post("/api/v1/sessions")

    assert response.status_code == 201
    assert response.json() == {"status": "ok"}

    # The session identifier is only transmitted through
    # the cookie, never in the response body.
    assert "id" not in response.json()


def test_delete_session_requires_authentication(
    client: TestClient,
):
    # A client without a session cookie cannot log out.
    anonymous = TestClient()
    response = anonymous.delete("/api/v1/sessions")

    assert response.status_code == 401


def test_session_cookie_attributes(client: TestClient):
    response = client.post("/api/v1/sessions")

    assert response.status_code == 201

    set_cookie = response.headers.get("set-cookie", "")
    assert settings.session_cookie_name in set_cookie
    assert "httponly" in set_cookie.lower()
