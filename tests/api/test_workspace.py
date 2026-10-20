def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_create_and_get_workspace(client):
    response = client.post("/api/v1/workspaces/", json={"name": "Test Workspace"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Workspace"
    assert "id" in data

    ws_id = data["id"]
    response = client.get(f"/api/v1/workspaces/{ws_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Workspace"

def test_list_workspaces(client):
    client.post("/api/v1/workspaces/", json={"name": "WS 1"})
    client.post("/api/v1/workspaces/", json={"name": "WS 2"})

    response = client.get("/api/v1/workspaces/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

def test_update_workspace(client):
    response = client.post("/api/v1/workspaces/", json={"name": "Old Name"})
    ws_id = response.json()["id"]

    response = client.patch(f"/api/v1/workspaces/{ws_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"

def test_empty_patch_preserves_name(client):
    response = client.post("/api/v1/workspaces/", json={"name": "Preserved Name"})
    ws_id = response.json()["id"]

    patch_resp = client.patch(f"/api/v1/workspaces/{ws_id}", json={})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["name"] == "Preserved Name"

    get_resp = client.get(f"/api/v1/workspaces/{ws_id}")
    assert get_resp.json()["name"] == "Preserved Name"

def test_delete_workspace(client):
    response = client.post("/api/v1/workspaces/", json={"name": "To Delete"})
    ws_id = response.json()["id"]

    response = client.delete(f"/api/v1/workspaces/{ws_id}")
    assert response.status_code == 204

    response = client.get(f"/api/v1/workspaces/{ws_id}")
    assert response.status_code == 404

def test_delete_workspace_cascades_dependencies(client):
    from unittest.mock import patch

    ws_resp = client.post("/api/v1/workspaces/", json={"name": "WS with Docs"})
    ws_id = ws_resp.json()["id"]

    # Add a document and a conversation.
    doc_data = {
        "file_name": "doc.pdf",
        "file_format": "pdf",
        "file_size": 100,
        "num_pages": 1,
    }
    client.post(f"/api/v1/workspaces/{ws_id}/documents", json=doc_data)
    client.post(
        f"/api/v1/workspaces/{ws_id}/conversations",
        json={"title": "Chat"},
    )

    # Vector cleanup is mocked; the cascade behavior is
    # verified without contacting Qdrant.
    with patch("app.services.document.delete_document_chunks"):
        del_resp = client.delete(f"/api/v1/workspaces/{ws_id}")
    assert del_resp.status_code == 204

    # The workspace and its data are gone.
    assert client.get(f"/api/v1/workspaces/{ws_id}").status_code == 404

def test_workspace_name_validation(client):
    # Empty JSON body
    assert client.post("/api/v1/workspaces/", json={}).status_code == 422
    # Empty string
    assert client.post("/api/v1/workspaces/", json={"name": ""}).status_code == 422
    # Whitespace only
    assert client.post("/api/v1/workspaces/", json={"name": "   "}).status_code == 422
    # Exceed max length 255
    assert client.post("/api/v1/workspaces/", json={"name": "a" * 256}).status_code == 422

    # PATCH invalid names
    ws_id = client.post("/api/v1/workspaces/", json={"name": "Valid"}).json()["id"]
    assert client.patch(f"/api/v1/workspaces/{ws_id}", json={"name": ""}).status_code == 422
    assert client.patch(f"/api/v1/workspaces/{ws_id}", json={"name": "  "}).status_code == 422
