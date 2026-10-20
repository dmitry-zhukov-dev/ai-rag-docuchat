from unittest.mock import patch

from fastapi.testclient import TestClient

from app.rag.generation import RAGAnswer


def _ready_workspace_with_document(client: TestClient) -> dict:
    ws = client.post(
        "/api/v1/workspaces/", json={"name": "Eval WS"}
    ).json()
    doc = client.post(
        f"/api/v1/workspaces/{ws['id']}/documents",
        json={
            "file_name": "guide.txt",
            "file_format": "txt",
            "file_size": 64,
            "indexing_status": "processing",
        },
    ).json()
    client.mark_document_ready(doc["id"])
    return {"workspace_id": ws["id"], "document_id": doc["id"]}


def test_evaluation_case_lifecycle(client: TestClient):
    setup = _ready_workspace_with_document(client)

    created = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/evaluations",
        json={
            "name": "Case 1",
            "question": "What is RAG?",
            "reference_answer": "RAG is retrieval-augmented generation.",
            "required_facts": ["retrieval-augmented generation"],
            "expected_sources": [
                {"document_id": setup["document_id"], "page": 1}
            ],
            "selected_document_ids": [setup["document_id"]],
        },
    )
    assert created.status_code == 201
    case = created.json()
    assert case["name"] == "Case 1"
    assert case["required_facts"] == [
        "retrieval-augmented generation"
    ]

    listed = client.get(
        f"/api/v1/workspaces/{setup['workspace_id']}/evaluations"
    ).json()
    assert len(listed) == 1

    patched = client.patch(
        f"/api/v1/evaluations/{case['id']}",
        json={"name": "Renamed"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Renamed"

    assert (
        client.delete(
            f"/api/v1/evaluations/{case['id']}"
        ).status_code
        == 204
    )
    assert (
        client.get(f"/api/v1/evaluations/{case['id']}").status_code
        == 404
    )


def test_evaluation_run_executes_real_rag_and_metrics(
    client: TestClient,
):
    setup = _ready_workspace_with_document(client)
    case = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/evaluations",
        json={
            "name": "Case",
            "question": "What is RAG?",
            "required_facts": ["retrieval-augmented generation"],
            "expected_sources": [
                {"document_id": setup["document_id"], "page": 1}
            ],
            "selected_document_ids": [setup["document_id"]],
        },
    ).json()

    def fake_answer_question(**kwargs):
        # The run must use the real retrieval contract
        # with the selected documents.
        assert kwargs["document_ids"] == [
            str(setup["document_id"])
        ]
        return RAGAnswer(
            answer=(
                "RAG is retrieval-augmented generation "
                "with a vector database."
            ),
            insufficient_context=False,
            sources=[
                {
                    "document_id": str(setup["document_id"]),
                    "filename": "guide.txt",
                    "page": 1,
                    "chunk_id": f"{setup['document_id']}:0",
                    "snippet": "RAG is retrieval-augmented...",
                }
            ],
            chunks=[],
        )

    with patch(
        "app.services.evaluation.answer_question",
        side_effect=fake_answer_question,
    ):
        response = client.post(
            f"/api/v1/evaluations/{case['id']}/runs"
        )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "completed"
    assert "retrieval-augmented generation" in run["answer"]
    assert run["actual_sources"][0]["document_id"] == str(
        setup["document_id"]
    )

    metrics = run["metrics"]
    assert metrics["retrieval_hit_rate"] == 1.0
    assert metrics["fact_coverage"] == 1.0
    assert metrics["source_precision"] == 1.0

    # Runs are listed and preserved per case.
    runs = client.get(
        f"/api/v1/evaluations/{case['id']}/runs"
    ).json()
    assert len(runs) == 1
    assert runs[0]["id"] == run["id"]

    fetched = client.get(
        f"/api/v1/evaluation-runs/{run['id']}"
    ).json()
    assert fetched["status"] == "completed"


def test_evaluation_run_records_failure(
    client: TestClient,
):
    from app.integrations.llm import GenerationError

    setup = _ready_workspace_with_document(client)
    case = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/evaluations",
        json={"name": "Case", "question": "What is RAG?"},
    ).json()

    with patch(
        "app.services.evaluation.answer_question",
        side_effect=GenerationError("provider failed"),
    ):
        response = client.post(
            f"/api/v1/evaluations/{case['id']}/runs"
        )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "failed"
    assert run["error"]
    assert run["answer"] is None


def test_evaluation_run_with_unready_selection_fails(
    client: TestClient,
):
    setup = _ready_workspace_with_document(client)
    unready = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/documents",
        json={
            "file_name": "processing.txt",
            "file_format": "txt",
            "file_size": 10,
        },
    ).json()

    case = client.post(
        f"/api/v1/workspaces/{setup['workspace_id']}/evaluations",
        json={
            "name": "Case",
            "question": "What?",
            "selected_document_ids": [unready["id"]],
        },
    ).json()

    response = client.post(
        f"/api/v1/evaluations/{case['id']}/runs"
    )

    assert response.status_code == 201
    run = response.json()
    assert run["status"] == "failed"
    assert "not ready" in run["error"]


def test_evaluation_routes_require_authentication():
    from fastapi.testclient import TestClient as TC

    from app.main import app

    anonymous = TC(app)
    response = anonymous.get("/api/v1/workspaces/1/evaluations")
    assert response.status_code == 401
