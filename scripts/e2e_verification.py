import sys
import time
import httpx
from app.db.session import SessionLocal
from app.db.models.document import Document
from app.db.models.conversation import Conversation


BASE_URL = "http://127.0.0.1:8000"


def run_e2e():
    print("=== Starting DocuChat End-to-End Verification ===")
    client_a = httpx.Client(base_url=BASE_URL, timeout=120.0)

    # -------------------------------------------------------------
    # Scenario 1: Open DocuChat without logging in
    # -------------------------------------------------------------
    print("\n--- Scenario 1: Initial Anonymous Session & Context ---")
    resp = client_a.post("/api/v1/sessions")
    assert resp.status_code == 201, f"Expected 201 from /sessions, got {resp.status_code}"
    cookie = resp.cookies.get("docuchat_session")
    assert cookie, "No docuchat_session cookie returned!"
    print(f" -> Session cookie acquired: {cookie[:10]}...")

    resp = client_a.post("/api/v1/sessions/context")
    assert resp.status_code == 200, f"Expected 200 from /sessions/context, got {resp.status_code}"
    ctx_a = resp.json()
    ws_a = ctx_a["workspace_id"]
    conv_a = ctx_a["conversation_id"]
    print(f" -> Default context: workspace_id={ws_a}, conversation_id={conv_a}")

    # -------------------------------------------------------------
    # Scenario 2 & 3: Upload TXT file and wait for processing
    # -------------------------------------------------------------
    print("\n--- Scenario 2 & 3: Upload TXT and Processing ---")
    doc_content = (
        "DocuChat is an intelligent document chat system built with Python, FastAPI, and Qdrant. "
        "Its primary security model uses anonymous sessions and HttpOnly cookies to isolate user data. "
        "The project version is 0.1.0 and was created in October 2026."
    )
    files = {"file": ("sample_docuchat.txt", doc_content.encode("utf-8"), "text/plain")}
    upload_url = f"/api/v1/workspaces/{ws_a}/documents/upload?conversation_id={conv_a}"
    resp = client_a.post(upload_url, files=files)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
    doc_data = resp.json()
    doc_id_1 = doc_data["id"]
    assert doc_data["disposition"] == "accepted"
    print(f" -> Uploaded doc_id={doc_id_1}, initial disposition={doc_data['disposition']}")

    # Poll status until completed
    status = doc_data["indexing_status"]
    for _ in range(15):
        if status == "completed":
            break
        time.sleep(1)
        resp = client_a.get(f"/api/v1/workspaces/{ws_a}/documents?conversation_id={conv_a}")
        docs = resp.json()
        target = next((d for d in docs if d["id"] == doc_id_1), None)
        assert target, "Uploaded document missing from list"
        status = target["indexing_status"]

    assert status == "completed", f"Document failed or stuck: {status}"
    print(f" -> Document {doc_id_1} processing completed successfully!")

    # -------------------------------------------------------------
    # Scenario 4: Ask a question grounded in the document
    # -------------------------------------------------------------
    print("\n--- Scenario 4: Chat Grounding & Source Citations ---")
    chat_url = f"/api/v1/conversations/{conv_a}/chat"
    resp = client_a.post(chat_url, json={"question": "What is the primary security model of DocuChat?"})
    assert resp.status_code == 200, f"Expected 200 from chat, got {resp.status_code}: {resp.text}"
    chat_result = resp.json()
    assert not chat_result["insufficient_context"], "Expected sufficient context, got insufficient_context=True"
    answer = chat_result["answer"]
    sources = chat_result["sources"]
    print(f" -> Answer: {answer}")
    assert len(sources) > 0, "No sources returned!"
    print(f" -> Sources returned ({len(sources)}):")
    for s in sources:
        print(f"     * filename: {s.get('filename')}, chunk: {s.get('chunk_id')}, snippet: {s.get('snippet')[:60]}...")
    assert any("anonymous sessions" in answer.lower() or "httponly" in answer.lower() or "security" in answer.lower() for _ in [1]), "Answer not grounded"

    # -------------------------------------------------------------
    # Scenario 5: Page reload restoration
    # -------------------------------------------------------------
    print("\n--- Scenario 5: Page Reload Restoration ---")
    resp = client_a.post("/api/v1/sessions")
    assert resp.status_code == 200, "Expected 200 on session reuse"
    resp = client_a.post("/api/v1/sessions/context")
    reloaded_ctx = resp.json()
    assert reloaded_ctx["workspace_id"] == ws_a, "Workspace ID not preserved across reload"
    assert reloaded_ctx["conversation_id"] == conv_a, "Conversation ID not preserved across reload"

    # Check documents list
    resp = client_a.get(f"/api/v1/workspaces/{ws_a}/documents?conversation_id={conv_a}")
    docs = resp.json()
    assert any(d["id"] == doc_id_1 for d in docs), "Document not restored on reload"

    # Check message history
    resp = client_a.get(f"/api/v1/conversations/{conv_a}/messages")
    messages = resp.json()
    assert len(messages) >= 2, f"Expected at least 2 messages, got {len(messages)}"
    print(f" -> Verified session, context, document ({len(docs)}), and messages ({len(messages)}) restored.")

    # -------------------------------------------------------------
    # Scenario 6: Re-upload exact same file
    # -------------------------------------------------------------
    print("\n--- Scenario 6: Re-upload Exact Same File ---")
    files_same = {"file": ("sample_docuchat.txt", doc_content.encode("utf-8"), "text/plain")}
    resp = client_a.post(upload_url, files=files_same)
    assert resp.status_code == 200, f"Expected 200 for duplicate, got {resp.status_code}"
    dup_data = resp.json()
    assert dup_data["disposition"] == "already_exists", f"Expected already_exists, got {dup_data['disposition']}"
    assert dup_data["id"] == doc_id_1, "Expected same document ID"
    print(" -> Confirmed: exact duplicate returned disposition='already_exists' with same document ID.")

    # -------------------------------------------------------------
    # Scenario 7: Upload identical content under different filename
    # -------------------------------------------------------------
    print("\n--- Scenario 7: Identical Content, Different Filename ---")
    files_diff_name = {"file": ("renamed_docuchat.txt", doc_content.encode("utf-8"), "text/plain")}
    resp = client_a.post(upload_url, files=files_diff_name)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    renamed_data = resp.json()
    assert renamed_data["disposition"] == "already_exists", f"Expected already_exists, got {renamed_data['disposition']}"
    assert renamed_data["id"] == doc_id_1, "Expected content-hash deduplication to match existing document"
    print(" -> Confirmed: content hash detected duplicate under different filename.")

    # -------------------------------------------------------------
    # Scenario 8: Same filename, different content
    # -------------------------------------------------------------
    print("\n--- Scenario 8: Same Filename, Different Content ---")
    diff_content = (
        "DocuChat Version 2 Release Notes: Added advanced multi-threaded background processing. "
        "The architecture supports hybrid vector search with BM25 keyword matching."
    )
    files_diff_content = {"file": ("sample_docuchat.txt", diff_content.encode("utf-8"), "text/plain")}
    resp = client_a.post(upload_url, files=files_diff_content)
    assert resp.status_code == 201, f"Expected 201, got {resp.status_code}"
    diff_data = resp.json()
    assert diff_data["disposition"] == "accepted"
    doc_id_2 = diff_data["id"]
    assert doc_id_2 != doc_id_1, "Expected distinct document ID for changed content"
    print(f" -> Confirmed: changed content created new document id={doc_id_2} (not silently discarded).")

    # -------------------------------------------------------------
    # Scenario 9: Second anonymous session isolation
    # -------------------------------------------------------------
    print("\n--- Scenario 9: Second Anonymous Session Isolation ---")
    client_b = httpx.Client(base_url=BASE_URL, timeout=120.0)
    resp_b = client_b.post("/api/v1/sessions")
    assert resp_b.status_code == 201
    cookie_b = resp_b.cookies.get("docuchat_session")
    assert cookie_b != cookie, "Client B received the same cookie!"
    resp_b = client_b.post("/api/v1/sessions/context")
    ctx_b = resp_b.json()
    ws_b = ctx_b["workspace_id"]
    conv_b = ctx_b["conversation_id"]
    assert ws_b != ws_a, "Client B received Client A's workspace!"
    assert conv_b != conv_a, "Client B received Client A's conversation!"

    # Attempt to access Client A's workspace documents
    resp = client_b.get(f"/api/v1/workspaces/{ws_a}/documents")
    assert resp.status_code == 403, f"Expected 403 accessing foreign workspace documents, got {resp.status_code}"

    # Attempt to access Client A's messages
    resp = client_b.get(f"/api/v1/conversations/{conv_a}/messages")
    assert resp.status_code == 403, f"Expected 403 accessing foreign messages, got {resp.status_code}"

    # Attempt chat in Client B's conversation (which has no documents uploaded)
    resp = client_b.post(f"/api/v1/conversations/{conv_b}/chat", json={"question": "What is DocuChat?"})
    assert resp.status_code == 400 or resp.json().get("insufficient_context") is True, (
        f"Client B should have no access to Client A's documents! Got: {resp.status_code} {resp.text}"
    )
    print(" -> Confirmed: Client B cannot access Client A's workspace, documents, messages, or retrieval results.")

    # -------------------------------------------------------------
    # Scenario 10: Legacy workspace-shared document compatibility
    # -------------------------------------------------------------
    print("\n--- Scenario 10: Legacy Workspace-Shared Document Compatibility ---")
    db = SessionLocal()
    try:
        legacy_doc = Document(
            workspace_id=ws_a,
            file_name="legacy_shared.txt",
            file_format="txt",
            file_size=120,
            num_pages=1,
            indexing_status="completed",
            conversation_id=None,
            file_hash=None,
        )
        db.add(legacy_doc)
        db.commit()
        db.refresh(legacy_doc)
        legacy_id = legacy_doc.id
        print(f" -> Created legacy document id={legacy_id} with conversation_id=NULL, file_hash=NULL")
    finally:
        db.close()

    # Client A should see the legacy document in its chat document list
    resp = client_a.get(f"/api/v1/workspaces/{ws_a}/documents?conversation_id={conv_a}")
    docs_a = resp.json()
    assert any(d["id"] == legacy_id for d in docs_a), "Client A should see legacy document"
    print(" -> Client A successfully listed legacy workspace-shared document.")

    # Client B should NOT see or access Client A's legacy document
    resp = client_b.get(f"/api/v1/workspaces/{ws_b}/documents?conversation_id={conv_b}")
    docs_b = resp.json()
    assert not any(d["id"] == legacy_id for d in docs_b), "Client B should NOT see Client A's legacy document"
    print(" -> Confirmed: Legacy documents adhere to approved workspace sharing and isolation policy.")

    # -------------------------------------------------------------
    # Scenario 11: Public UI inspection
    # -------------------------------------------------------------
    print("\n--- Scenario 11: Public UI Surface Inspection ---")
    resp = client_a.get("/")
    assert resp.status_code == 200
    html = resp.text
    forbidden_terms = ["Evaluation", "New Test Case", "Create Workspace", "Create Conversation", "evaluation_cases"]
    for term in forbidden_terms:
        assert term.lower() not in html.lower(), f"Forbidden administrative term '{term}' exposed in public UI!"
    print(" -> Confirmed: Public interface exposes only simple upload & chat, with no administrative evaluation or manual workspace/chat controls.")

    print("\nALL 11 END-TO-END SCENARIOS VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    run_e2e()
