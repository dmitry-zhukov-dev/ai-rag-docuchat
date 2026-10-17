def test_document_lifecycle(client):
    # 1. Create a workspace
    ws_resp = client.post("/api/v1/workspaces/", json={"name": "Doc Workspace"})
    assert ws_resp.status_code == 201
    ws_id = ws_resp.json()["id"]

    # 2. Create document metadata in workspace
    doc_data = {
        "file_name": "contract.pdf",
        "file_format": "pdf",
        "file_size": 2048,
        "num_pages": 5,
        "indexing_status": "processing"
    }
    create_resp = client.post(f"/api/v1/workspaces/{ws_id}/documents", json=doc_data)
    assert create_resp.status_code == 201
    doc = create_resp.json()
    assert doc["file_name"] == "contract.pdf"
    assert doc["workspace_id"] == ws_id
    doc_id = doc["id"]

    # 3. Retrieve document by ID
    get_resp = client.get(f"/api/v1/documents/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["file_size"] == 2048

    # 4. List documents in workspace
    list_resp = client.get(f"/api/v1/workspaces/{ws_id}/documents")
    assert list_resp.status_code == 200
    docs = list_resp.json()
    assert len(docs) == 1
    assert docs[0]["id"] == doc_id

    # 5. Filter by indexing_status
    filter_resp = client.get(f"/api/v1/workspaces/{ws_id}/documents?indexing_status=completed")
    assert filter_resp.status_code == 200
    assert len(filter_resp.json()) == 0

    filter_resp2 = client.get(f"/api/v1/workspaces/{ws_id}/documents?indexing_status=processing")
    assert filter_resp2.status_code == 200
    assert len(filter_resp2.json()) == 1

    # 6. Partially update document metadata
    patch_resp = client.patch(f"/api/v1/documents/{doc_id}", json={"indexing_status": "completed"})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["indexing_status"] == "completed"
    assert patch_resp.json()["file_name"] == "contract.pdf"  # Preserved

    # 7. Non-existent document 404
    assert client.get("/api/v1/documents/99999").status_code == 404
    assert client.patch("/api/v1/documents/99999", json={"file_name": "new.pdf"}).status_code == 404

    # 8. Non-existent workspace 404
    assert client.post("/api/v1/workspaces/99999/documents", json=doc_data).status_code == 404
    assert client.get("/api/v1/workspaces/99999/documents").status_code == 404

    # 9. Invalid input validation 422
    invalid_data = {"file_name": "no_size.pdf", "file_format": "pdf"}
    assert client.post(f"/api/v1/workspaces/{ws_id}/documents", json=invalid_data).status_code == 422

    # 10. Workspace isolation
    ws2_resp = client.post("/api/v1/workspaces/", json={"name": "Other Workspace"})
    ws2_id = ws2_resp.json()["id"]
    ws2_docs = client.get(f"/api/v1/workspaces/{ws2_id}/documents").json()
    assert len(ws2_docs) == 0
