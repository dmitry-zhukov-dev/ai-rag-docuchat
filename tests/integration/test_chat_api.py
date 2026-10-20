from unittest.mock import patch

from fastapi.testclient import TestClient

from app.rag.generation import RAGAnswer


def _ready_workspace_with_document(client: TestClient) -> dict:
    """Create a workspace with one ready document."""
    ws = client.post(
        "/api/v1/workspaces/", json={"name": "Chat WS"}
    ).json()
    doc = client.post(
        f"/api/v1/workspaces/{ws['id']}/documents",
        json={
            "file_name": "manual.pdf",
            "file_format": "pdf",
            "file_size": 2048,
            "num_pages": 3,
            "indexing_status": "processing",
        },
    ).json()
    client.mark_document_ready(doc["id"])
    return {"workspace_id": ws["id"], "document_id": str(doc["id"])}


def test_chat_returns_answer_with_sources(
    client: TestClient, monkeypatch
):
    setup = _ready_workspace_with_document(client)
    conversation = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/conversations",
        json={"title": "Chat"},
    ).json()

    def fake_answer_question(**kwargs):
        assert kwargs["workspace_id"] == str(
            setup["workspace_id"]
        )
        assert kwargs["document_ids"] == [setup["document_id"]]
        assert kwargs["accessible_document_ids"] == {
            setup["document_id"]
        }
        return RAGAnswer(
            answer="RAG stands for Retrieval-Augmented Generation.",
            insufficient_context=False,
            sources=[
                {
                    "document_id": setup["document_id"],
                    "filename": "manual.pdf",
                    "page": 2,
                    "chunk_id": f"{setup['document_id']}:0",
                    "snippet": "RAG stands for...",
                }
            ],
            chunks=[],
        )

    with patch(
        "app.services.chat.answer_question",
        side_effect=fake_answer_question,
    ):
        response = client.post(
            f"/api/v1/conversations/{conversation['id']}/chat",
            json={"question": "What does RAG stand for?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == conversation["id"]
    assert data["question"] == "What does RAG stand for?"
    assert (
        data["answer"]
        == "RAG stands for Retrieval-Augmented Generation."
    )
    assert data["insufficient_context"] is False
    assert len(data["sources"]) == 1
    assert data["sources"][0]["filename"] == "manual.pdf"
    assert data["sources"][0]["page"] == 2
    assert data["sources"][0]["chunk_id"] == (
        f"{setup['document_id']}:0"
    )

    # The answer and its sources are persisted and restored.
    messages = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages"
    ).json()
    assert len(messages) == 2
    assert messages[0]["sender_role"] == "user"
    assert messages[1]["sender_role"] == "assistant"
    assert messages[1]["sources"][0]["chunk_id"] == (
        f"{setup['document_id']}:0"
    )


def test_chat_reports_insufficient_context(
    client: TestClient, monkeypatch
):
    setup = _ready_workspace_with_document(client)
    conversation = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/conversations",
        json={"title": "Chat"},
    ).json()

    with patch(
        "app.services.chat.answer_question",
        return_value=RAGAnswer(
            answer="",
            insufficient_context=True,
            sources=[],
            chunks=[],
        ),
    ):
        response = client.post(
            f"/api/v1/conversations/{conversation['id']}/chat",
            json={"question": "What is not in the documents?"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["insufficient_context"] is True
    assert data["answer"] == ""
    assert data["sources"] == []


def test_chat_without_ready_documents_is_rejected(
    client: TestClient,
):
    ws = client.post(
        "/api/v1/workspaces/", json={"name": "Empty WS"}
    ).json()
    conversation = client.post(
        f"/api/v1/workspaces/{ws['id']}/conversations",
        json={"title": "Chat"},
    ).json()

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/chat",
        json={"question": "Anything?"},
    )

    assert response.status_code == 409


def test_chat_generation_failure_keeps_question_without_answer(
    client: TestClient,
):
    from app.integrations.llm import GenerationError

    setup = _ready_workspace_with_document(client)
    conversation = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/conversations",
        json={"title": "Chat"},
    ).json()

    with patch(
        "app.services.chat.answer_question",
        side_effect=GenerationError(
            "The answer could not be generated."
        ),
    ):
        response = client.post(
            f"/api/v1/conversations/{conversation['id']}/chat",
            json={"question": "What does RAG stand for?"},
        )

    # No fictitious successful answer is returned.
    assert response.status_code == 502

    # The question itself is preserved in history.
    messages = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages"
    ).json()
    assert len(messages) == 1
    assert messages[0]["sender_role"] == "user"


def test_chat_for_unknown_conversation(client: TestClient):
    response = client.post(
        "/api/v1/conversations/99999/chat",
        json={"question": "Anything?"},
    )

    assert response.status_code == 404


def _add_ready_document(client: TestClient, workspace_id: int, name: str) -> dict:
    document = client.post(
        f"/api/v1/workspaces/{workspace_id}/documents",
        json={
            "file_name": name,
            "file_format": "txt",
            "file_size": 64,
            "indexing_status": "processing",
        },
    ).json()
    client.mark_document_ready(document["id"])
    return document


def test_chat_with_explicit_document_selection(
    client: TestClient, monkeypatch
):
    setup = _ready_workspace_with_document(client)
    other = _add_ready_document(
        client, setup["workspace_id"], "other.txt"
    )
    conversation = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/conversations",
        json={"title": "Chat"},
    ).json()

    def fake_answer_question(**kwargs):
        # Only the selected document may be searched.
        assert kwargs["document_ids"] == [setup["document_id"]]
        assert kwargs["accessible_document_ids"] == {
            setup["document_id"]
        }
        return RAGAnswer(
            answer="Selected answer",
            insufficient_context=False,
            sources=[],
            chunks=[],
        )

    with patch(
        "app.services.chat.answer_question",
        side_effect=fake_answer_question,
    ):
        response = client.post(
            f"/api/v1/conversations/{conversation['id']}/chat",
            json={
                "question": "Question?",
                "document_ids": [int(setup["document_id"])],
            },
        )

    assert response.status_code == 200
    assert response.json()["answer"] == "Selected answer"


def test_chat_with_omitted_document_ids_uses_all_ready_documents(
    client: TestClient, monkeypatch
):
    setup = _ready_workspace_with_document(client)
    other = _add_ready_document(
        client, setup["workspace_id"], "other.txt"
    )
    conversation = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/conversations",
        json={"title": "Chat"},
    ).json()

    def fake_answer_question(**kwargs):
        # Omission means every ready document in the
        # workspace, in any order.
        assert set(kwargs["document_ids"]) == {
            setup["document_id"],
            str(other["id"]),
        }
        return RAGAnswer(
            answer="Answer",
            insufficient_context=False,
            sources=[],
            chunks=[],
        )

    with patch(
        "app.services.chat.answer_question",
        side_effect=fake_answer_question,
    ):
        response = client.post(
            f"/api/v1/conversations/{conversation['id']}/chat",
            json={"question": "Question?"},
        )

    assert response.status_code == 200


def test_chat_with_empty_document_selection_reports_insufficient_context(
    client: TestClient, monkeypatch
):
    setup = _ready_workspace_with_document(client)
    conversation = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/conversations",
        json={"title": "Chat"},
    ).json()

    def fake_answer_question(**kwargs):
        # An empty selection must not become an
        # unrestricted search.
        assert kwargs["document_ids"] == []
        return RAGAnswer(
            answer="",
            insufficient_context=True,
            sources=[],
            chunks=[],
        )

    with patch(
        "app.services.chat.answer_question",
        side_effect=fake_answer_question,
    ):
        response = client.post(
            f"/api/v1/conversations/{conversation['id']}/chat",
            json={"question": "Question?", "document_ids": []},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["insufficient_context"] is True


def test_chat_with_unknown_selected_document_is_rejected(
    client: TestClient,
):
    setup = _ready_workspace_with_document(client)
    conversation = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/conversations",
        json={"title": "Chat"},
    ).json()

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/chat",
        json={"question": "Question?", "document_ids": [99999]},
    )

    assert response.status_code == 400


def test_chat_with_unready_selected_document_is_rejected(
    client: TestClient,
):
    setup = _ready_workspace_with_document(client)
    unready = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/documents",
        json={
            "file_name": "processing.txt",
            "file_format": "txt",
            "file_size": 10,
            "indexing_status": "processing",
        },
    ).json()
    conversation = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/conversations",
        json={"title": "Chat"},
    ).json()

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/chat",
        json={
            "question": "Question?",
            "document_ids": [unready["id"]],
        },
    )

    assert response.status_code == 400


def test_chat_rejects_duplicate_selected_documents(
    client: TestClient,
):
    setup = _ready_workspace_with_document(client)
    conversation = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/conversations",
        json={"title": "Chat"},
    ).json()

    response = client.post(
        f"/api/v1/conversations/{conversation['id']}/chat",
        json={
            "question": "Question?",
            "document_ids": [
                int(setup["document_id"]),
                int(setup["document_id"]),
            ],
        },
    )

    assert response.status_code == 400
