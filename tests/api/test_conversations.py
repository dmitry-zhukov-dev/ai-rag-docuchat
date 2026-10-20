def test_create_conversation_in_existing_workspace(client):
    ws_resp = client.post("/api/v1/workspaces/", json={"name": "Conv Workspace"})
    ws_id = ws_resp.json()["id"]

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/conversations", json={"title": "Project Chat"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Project Chat"
    assert data["workspace_id"] == ws_id
    assert "id" in data
    assert "created_at" in data

def test_create_conversation_in_nonexistent_workspace(client):
    resp = client.post(
        "/api/v1/workspaces/99999/conversations", json={"title": "Chat"}
    )
    assert resp.status_code == 404

def test_list_conversations_for_workspace_and_isolation(client):
    ws1 = client.post("/api/v1/workspaces/", json={"name": "WS1"}).json()["id"]
    ws2 = client.post("/api/v1/workspaces/", json={"name": "WS2"}).json()["id"]

    client.post(f"/api/v1/workspaces/{ws1}/conversations", json={"title": "WS1 Chat"})
    client.post(f"/api/v1/workspaces/{ws2}/conversations", json={"title": "WS2 Chat"})

    resp1 = client.get(f"/api/v1/workspaces/{ws1}/conversations")
    assert resp1.status_code == 200
    convs1 = resp1.json()
    assert len(convs1) == 1
    assert convs1[0]["title"] == "WS1 Chat"

    resp2 = client.get(f"/api/v1/workspaces/{ws2}/conversations")
    assert resp2.status_code == 200
    convs2 = resp2.json()
    assert len(convs2) == 1
    assert convs2[0]["title"] == "WS2 Chat"

def test_get_conversation_by_id_and_not_found(client):
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}).json()["id"]
    conv = client.post(
        f"/api/v1/workspaces/{ws}/conversations", json={"title": "Chat 1"}
    ).json()

    resp = client.get(f"/api/v1/conversations/{conv['id']}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Chat 1"

    assert client.get("/api/v1/conversations/99999").status_code == 404

def test_add_and_list_messages(client):
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}).json()["id"]
    conv_id = client.post(
        f"/api/v1/workspaces/{ws}/conversations", json={"title": "Chat"}
    ).json()["id"]

    # Add message
    msg_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"sender_role": "user", "text": "Hello world!"},
    )
    assert msg_resp.status_code == 201
    msg = msg_resp.json()
    assert msg["sender_role"] == "user"
    assert msg["text"] == "Hello world!"
    assert msg["conversation_id"] == conv_id
    assert msg["sources"] is None

    # List messages
    list_resp = client.get(f"/api/v1/conversations/{conv_id}/messages")
    assert list_resp.status_code == 200
    messages = list_resp.json()
    assert len(messages) == 1
    assert messages[0]["id"] == msg["id"]

def test_messages_nonexistent_conversation(client):
    assert (
        client.get("/api/v1/conversations/99999/messages").status_code == 404
    )
    assert (
        client.post(
            "/api/v1/conversations/99999/messages",
            json={"sender_role": "user", "text": "Hello"},
        ).status_code
        == 404
    )

def test_pagination_and_validation(client):
    ws = client.post("/api/v1/workspaces/", json={"name": "WS"}).json()["id"]
    conv_id = client.post(f"/api/v1/workspaces/{ws}/conversations", json={}).json()[
        "id"
    ]

    for i in range(5):
        client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            json={"sender_role": "user", "text": f"Msg {i}"},
        )

    # Test limit and skip
    resp = client.get(f"/api/v1/conversations/{conv_id}/messages?skip=2&limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["text"] == "Msg 2"
    assert data[1]["text"] == "Msg 3"

    # Validation failure: negative skip
    bad_skip = client.get(f"/api/v1/conversations/{conv_id}/messages?skip=-1")
    assert bad_skip.status_code == 422

    # Validation failure: empty message text
    bad_msg = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"sender_role": "user", "text": ""},
    )
    assert bad_msg.status_code == 422
