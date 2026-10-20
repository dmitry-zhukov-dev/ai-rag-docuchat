from io import BytesIO

from fastapi.testclient import TestClient

from app.services.file_storage import UPLOAD_DIR


def test_document_upload(client: TestClient, monkeypatch):
    # Replace real ingestion to avoid writing test data to Qdrant.
    def fake_ingest_document(
        file_path: str,
        document_id: str,
        workspace_id: str,
        filename: str,
    ) -> int:
        assert file_path
        assert document_id
        assert workspace_id
        assert filename
        return 1

    monkeypatch.setattr(
        "app.api.routes.document.ingest_document",
        fake_ingest_document,
    )

    # Remember existing files so we don't delete user data.
    files_before = set(UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else set()

    try:
        # 1. Create workspace
        response = client.post(
            "/api/v1/workspaces/",
            json={"name": "Test Workspace"},
        )
        assert response.status_code == 201
        workspace_id = response.json()["id"]

        # 2. Upload a small TXT file
        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/documents/upload",
            files={
                "file": (
                    "test.txt",
                    BytesIO(b"RAG stands for Retrieval-Augmented Generation."),
                    "text/plain",
                )
            },
        )
        assert response.status_code == 201

        document = response.json()
        document_id = document["id"]

        assert document["workspace_id"] == workspace_id
        assert document["file_name"] == "test.txt"
        assert document["file_format"] == "txt"
        assert document["indexing_status"] == "completed"

        # 3. Read the document
        response = client.get(f"/api/v1/documents/{document_id}")
        assert response.status_code == 200
        assert response.json()["id"] == document_id

        # 4. Check the document appears in the workspace
        response = client.get(
            f"/api/v1/workspaces/{workspace_id}/documents"
        )
        assert response.status_code == 200
        assert any(
            item["id"] == document_id
            for item in response.json()
        )

        # 5. Check that the uploaded file was saved
        files_after = set(UPLOAD_DIR.glob("*"))
        new_files = files_after - files_before
        assert len(new_files) == 1

        saved_file = new_files.pop()
        assert saved_file.is_file()
        assert saved_file.read_bytes() == (
            b"RAG stands for Retrieval-Augmented Generation."
        )

    finally:
        # Remove only files created during this test.
        files_after = set(UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else set()
        for path in files_after - files_before:
            if path.is_file():
                path.unlink()


def test_document_update_and_not_found(client: TestClient):
    # Create workspace
    response = client.post(
        "/api/v1/workspaces/",
        json={"name": "Test Workspace"},
    )
    assert response.status_code == 201
    workspace_id = response.json()["id"]

    # Create document metadata
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        json={
            "file_name": "manual.txt",
            "file_format": "txt",
            "file_size": 100,
            "indexing_status": "processing",
        },
    )
    assert response.status_code == 201
    document_id = response.json()["id"]

    # Update document status
    response = client.patch(
        f"/api/v1/documents/{document_id}",
        json={"indexing_status": "completed"},
    )
    assert response.status_code == 200
    assert response.json()["indexing_status"] == "completed"

    # Read updated document
    response = client.get(f"/api/v1/documents/{document_id}")
    assert response.status_code == 200
    assert response.json()["indexing_status"] == "completed"

    # Nonexistent document should return 404
    response = client.get("/api/v1/documents/999999")
    assert response.status_code == 404

    # Nonexistent workspace should return 404
    response = client.get(
        "/api/v1/workspaces/999999/documents"
    )
    assert response.status_code == 404


def test_metadata_creation_always_starts_processing(client):
    """A metadata-only endpoint cannot fabricate a ready document."""
    ws_resp = client.post("/api/v1/workspaces/", json={"name": "WS"})
    ws_id = ws_resp.json()["id"]

    response = client.post(
        f"/api/v1/workspaces/{ws_id}/documents",
        json={
            "file_name": "ghost.pdf",
            "file_format": "pdf",
            "file_size": 100,
            # Requesting a ready state must be ignored.
            "indexing_status": "completed",
        },
    )

    assert response.status_code == 201
    assert response.json()["indexing_status"] == "processing"


def test_upload_failure_compensates_artifacts(client, monkeypatch):
    from unittest.mock import patch

    from app.services.file_storage import UPLOAD_DIR

    ws_resp = client.post("/api/v1/workspaces/", json={"name": "WS"})
    ws_id = ws_resp.json()["id"]

    files_before = set(UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else set()

    def failing_ingest(**kwargs):
        raise RuntimeError("indexing exploded")

    try:
        with patch(
            "app.api.routes.document.ingest_document",
            side_effect=failing_ingest,
        ) as ingest_mock, patch(
            "app.api.routes.document.delete_document_chunks"
        ) as cleanup_mock:
            response = client.post(
                f"/api/v1/workspaces/{ws_id}/documents/upload",
                files={
                    "file": (
                        "broken.pdf",
                        BytesIO(b"%PDF-1.4 broken"),
                        "application/pdf",
                    )
                },
            )

        assert response.status_code == 500
        ingest_mock.assert_called_once()

        # Partially indexed vector points are removed.
        cleanup_mock.assert_called_once()

        # The document remains in a diagnosable failed state.
        docs = client.get(
            f"/api/v1/workspaces/{ws_id}/documents"
        ).json()
        assert len(docs) == 1
        assert docs[0]["indexing_status"] == "failed"
        assert docs[0]["error_message"]

        # The stored file was removed.
        files_after = set(UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else set()
        assert not (files_after - files_before)

    finally:
        files_after = set(UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else set()
        for path in files_after - files_before:
            if path.is_file():
                path.unlink()


def test_document_deletion_is_safely_repeatable(
    client: TestClient,
):
    from unittest.mock import patch

    ws_resp = client.post(
        "/api/v1/workspaces/", json={"name": "WS"}
    )
    ws_id = ws_resp.json()["id"]

    doc_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/documents",
        json={
            "file_name": "note.txt",
            "file_format": "txt",
            "file_size": 10,
        },
    )
    document_id = doc_resp.json()["id"]

    with patch(
        "app.services.document.delete_document_chunks"
    ):
        first = client.delete(f"/api/v1/documents/{document_id}")
        assert first.status_code == 204

        # Repeating the deletion is safe and reports
        # the document as gone.
        second = client.delete(
            f"/api/v1/documents/{document_id}"
        )
        assert second.status_code == 404
