import sys
from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.repositories.session import SessionRepository
from app.repositories.workspace import WorkspaceRepository
from app.repositories.document import DocumentRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository


def main():
    print("Beginning PostgreSQL persistence verification...")
    db = SessionLocal()

    session_repo = SessionRepository()
    workspace_repo = WorkspaceRepository()
    document_repo = DocumentRepository()
    conversation_repo = ConversationRepository()
    message_repo = MessageRepository()

    test_session_id = "test_persistence_check_session_001"
    created_workspace_id = None
    created_doc_id = None
    created_conv_id = None
    created_msg_ids = []

    try:
        # 1. Session Persistence
        print("[1/5] Testing Session persistence...")
        expires = datetime.now(timezone.utc) + timedelta(days=1)
        sess = session_repo.create(db, session_id=test_session_id, expires_at=expires)
        read_sess = session_repo.get(db, test_session_id)
        assert read_sess is not None, "Failed to read created session"
        assert read_sess.id == test_session_id, f"Session ID mismatch: {read_sess.id}"
        print(f" -> Session created & verified: id={read_sess.id}")

        # 2. Workspace Persistence
        print("[2/5] Testing Workspace persistence...")
        ws = workspace_repo.create(db, name="Persistence Test Workspace", session_id=test_session_id)
        created_workspace_id = ws.id
        read_ws = workspace_repo.get(db, created_workspace_id)
        assert read_ws is not None, "Failed to read created workspace"
        assert read_ws.name == "Persistence Test Workspace", f"Workspace name mismatch: {read_ws.name}"
        assert read_ws.session_id == test_session_id, "Workspace session_id mismatch"
        print(f" -> Workspace created & verified: id={read_ws.id}, name={read_ws.name}")

        # 3. Document Persistence
        print("[3/5] Testing Document persistence...")
        doc = document_repo.create(
            db,
            workspace_id=created_workspace_id,
            file_name="persistence_sample.txt",
            file_format="txt",
            file_size=512,
            num_pages=1,
            indexing_status="processing",
            file_path="uploads/persistence_sample.txt",
        )
        created_doc_id = doc.id
        read_doc = document_repo.get(db, created_doc_id)
        assert read_doc is not None, "Failed to read created document"
        assert read_doc.file_name == "persistence_sample.txt", "Document file_name mismatch"
        assert read_doc.workspace_id == created_workspace_id, "Document workspace_id mismatch"
        
        # Test updating document status and error_message
        document_repo.update(db, db_obj=read_doc, indexing_status="ready", error_message=None)
        refreshed_doc = document_repo.get(db, created_doc_id)
        assert refreshed_doc.indexing_status == "ready", "Document update failed"
        print(f" -> Document created, updated & verified: id={refreshed_doc.id}, status={refreshed_doc.indexing_status}")

        # 4. Conversation & Messages Persistence
        print("[4/5] Testing Conversation & Message persistence...")
        conv = conversation_repo.create(db, workspace_id=created_workspace_id, title="Persistence Check Conv")
        created_conv_id = conv.id
        read_conv = conversation_repo.get(db, created_conv_id)
        assert read_conv is not None, "Failed to read created conversation"
        assert read_conv.title == "Persistence Check Conv", "Conversation title mismatch"

        m1 = message_repo.create(
            db,
            conversation_id=created_conv_id,
            sender_role="user",
            text="What is persistence?",
        )
        created_msg_ids.append(m1.id)

        m2 = message_repo.create(
            db,
            conversation_id=created_conv_id,
            sender_role="assistant",
            text="Persistence is data surviving process restarts.",
            sources=[{"document_id": created_doc_id, "file_name": "persistence_sample.txt", "page": 1, "snippet": "data surviving"}],
        )
        created_msg_ids.append(m2.id)

        messages = message_repo.get_by_conversation(db, conversation_id=created_conv_id)
        assert len(messages) == 2, f"Expected 2 messages, got {len(messages)}"
        assert messages[0].sender_role == "user"
        assert messages[1].sender_role == "assistant"
        assert messages[1].sources[0]["document_id"] == created_doc_id
        print(f" -> Conversation & 2 messages (with JSON sources) verified successfully.")

        # 5. Cleanup of test-created records only
        print("[5/5] Cleaning up test records...")
        for mid in created_msg_ids:
            message_repo.delete(db, id=mid)
        if created_conv_id:
            conversation_repo.delete(db, id=created_conv_id)
        if created_doc_id:
            document_repo.delete(db, id=created_doc_id)
        if created_workspace_id:
            workspace_repo.delete(db, id=created_workspace_id)
        session_repo.delete(db, session_id=test_session_id)

        # Confirm cleanup
        assert session_repo.get(db, test_session_id) is None, "Test session was not cleaned up"
        assert workspace_repo.get(db, created_workspace_id) is None, "Test workspace was not cleaned up"
        print(" -> Cleanup verified: all test records removed.")

        print("PERSISTENCE VERIFICATION PASSED SUCCESSFULLY!")

    except Exception as e:
        print(f"ERROR during persistence check: {e}")
        # Attempt cleanup on error
        try:
            for mid in created_msg_ids:
                message_repo.delete(db, id=mid)
            if created_conv_id:
                conversation_repo.delete(db, id=created_conv_id)
            if created_doc_id:
                document_repo.delete(db, id=created_doc_id)
            if created_workspace_id:
                workspace_repo.delete(db, id=created_workspace_id)
            session_repo.delete(db, session_id=test_session_id)
        except Exception:
            pass
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

