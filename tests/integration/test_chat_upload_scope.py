"""Prepared regression tests. Not executed; SQLite cannot verify PostgreSQL row locks."""
from unittest.mock import Mock

import pytest


@pytest.fixture
def uploads(client, monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.file_storage.UPLOAD_DIR", tmp_path)
    monkeypatch.setattr("app.services.document.UPLOAD_DIR", tmp_path)
    ingest = Mock(return_value=1)
    cleanup = Mock()
    monkeypatch.setattr("app.api.routes.document.ingest_document", ingest)
    monkeypatch.setattr("app.api.routes.document.delete_document_chunks", cleanup)
    context = client.post("/api/v1/sessions/context").json()

    def upload(content=b"Document content", name="note.txt", chat=None, retry=False):
        chat = chat or context["conversation_id"]
        return client.post(
            f"/api/v1/workspaces/{context['workspace_id']}/documents/upload"
            f"?conversation_id={chat}&retry={'true' if retry else 'false'}",
            files={"file": (name, content, "text/plain")},
        )
    return context, upload, ingest, cleanup


def test_content_identity_and_versions(client, uploads):
    context, upload, ingest, _ = uploads
    first = upload()
    assert first.status_code == 201
    for name in ("note.txt", "renamed.txt"):
        duplicate = upload(name=name)
        assert duplicate.status_code == 200
        assert duplicate.json()["id"] == first.json()["id"]
        assert duplicate.json()["disposition"] == "already_exists"
    assert ingest.call_count == 1
    changed = upload(content=b"Changed content")
    assert changed.json()["id"] != first.json()["id"]
    assert ingest.call_count == 2
    other_chat = client.post(
        f"/api/v1/workspaces/{context['workspace_id']}/conversations", json={}
    ).json()["id"]
    independent = upload(chat=other_chat)
    assert independent.json()["id"] != first.json()["id"]
    assert ingest.call_count == 3
    listed = client.get(
        f"/api/v1/workspaces/{context['workspace_id']}/documents?conversation_id={other_chat}"
    ).json()
    assert [doc["id"] for doc in listed] == [independent.json()["id"]]
    response = client.post(f"/api/v1/conversations/{other_chat}/chat", json={
        "question": "Question", "document_ids": [first.json()["id"]],
    })
    assert response.status_code == 400


def test_failed_upload_requires_explicit_retry(uploads):
    _, upload, ingest, cleanup = uploads
    ingest.side_effect = RuntimeError("private diagnostic")
    assert upload().status_code == 500
    failed = upload()
    assert failed.json()["disposition"] == "failed"
    assert ingest.call_count == 1
    ingest.side_effect = None
    retried = upload(retry=True)
    assert retried.status_code == 201
    assert retried.json()["id"] == failed.json()["id"]
    assert retried.json()["disposition"] == "retried"
    assert retried.json()["error_message"] is None
    assert ingest.call_count == 2
    assert cleanup.call_count == 2  # compensation, then retry cleanup


def test_processing_claim_is_reused(client, uploads, db_session):
    from app.db.models.document import Document
    _, upload, ingest, _ = uploads
    first = upload().json()
    doc = db_session.get(Document, first["id"])
    doc.indexing_status = "processing"
    db_session.commit()
    repeated = upload(retry=True)
    assert repeated.json()["disposition"] == "processing"
    assert ingest.call_count == 1
    assert client.delete(f"/api/v1/documents/{doc.id}").status_code == 409


def test_other_identity_cannot_use_context(client, uploads):
    context, upload, ingest, _ = uploads
    doc = upload().json()
    client.cookies.clear()
    assert client.post("/api/v1/sessions").status_code == 201
    assert client.get(f"/api/v1/documents/{doc['id']}").status_code == 404
    assert upload().status_code == 404
    assert client.get(f"/api/v1/conversations/{context['conversation_id']}/messages").status_code == 404
    assert ingest.call_count == 1


def test_legacy_documents_remain_workspace_shared(client, uploads):
    context, upload, _, _ = uploads
    legacy = client.post(f"/api/v1/workspaces/{context['workspace_id']}/documents", json={
        "file_name": "old.txt", "file_format": "txt", "file_size": 10,
    }).json()
    upload()
    other_chat = client.post(
        f"/api/v1/workspaces/{context['workspace_id']}/conversations", json={}
    ).json()["id"]
    listed = client.get(
        f"/api/v1/workspaces/{context['workspace_id']}/documents?conversation_id={other_chat}"
    ).json()
    assert [doc["id"] for doc in listed] == [legacy["id"]]
