import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.services.workspace import WorkspaceService
from app.services.document import DocumentService
from app.services.conversation import ConversationService
from app.services.evaluation import EvaluationService

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_services(db_session):
    ws_svc = WorkspaceService()
    doc_svc = DocumentService()
    conv_svc = ConversationService()
    eval_svc = EvaluationService()

    # Workspace
    ws = ws_svc.create_workspace(db_session, name="WS1", session_id="session-1")
    assert ws_svc.get_workspace(db_session, ws.id).name == "WS1"

    # Document
    doc = doc_svc.create_document(db_session, workspace_id=ws.id, file_name="t.pdf", file_format="pdf", file_size=100)
    assert len(doc_svc.list_workspace_documents(db_session, ws.id)) == 1

    # Conversation & Message
    conv = conv_svc.create_conversation(db_session, workspace_id=ws.id, title="Test Chat")
    assert conv is not None
    assert conv.title == "Test Chat"
    
    msg = conv_svc.add_message(db_session, conversation_id=conv.id, sender_role="user", text="hi")
    assert msg is not None
    assert msg.text == "hi"
    assert len(conv_svc.list_messages(db_session, conv.id)) == 1

    # Missing entity checks
    assert conv_svc.create_conversation(db_session, workspace_id=999) is None
    assert conv_svc.list_workspace_conversations(db_session, workspace_id=999) is None
    assert conv_svc.add_message(db_session, conversation_id=999, sender_role="user", text="hi") is None
    assert conv_svc.list_messages(db_session, conversation_id=999) is None

    # Eval
    case = eval_svc.create_case(db_session, workspace_id=ws.id, name="C1", question="Q")
    assert eval_svc.get_case(db_session, case.id) is not None

    # Runs execute the real RAG pipeline; here the
    # provider is mocked to keep the unit test isolated.
    from unittest.mock import patch

    from app.rag.generation import RAGAnswer

    with patch(
        "app.services.evaluation.answer_question",
        return_value=RAGAnswer(
            answer="A",
            insufficient_context=False,
            sources=[],
            chunks=[],
        ),
    ):
        run = eval_svc.run_case(db_session, case.id)

    assert run.status == "completed"
    assert len(eval_svc.list_runs(db_session, case.id)) == 1

    updated = eval_svc.update_case(
        db_session, case_id=case.id, name="C1 Renamed"
    )
    assert updated.name == "C1 Renamed"

    assert eval_svc.delete_case(db_session, case.id) is True
    assert eval_svc.list_cases(db_session, workspace_id=ws.id) == []


def test_delete_document_reports_vector_cleanup_failure(
    db_session, monkeypatch
):
    from unittest.mock import patch

    doc_svc = DocumentService()
    ws_svc = WorkspaceService()

    ws = ws_svc.create_workspace(
        db_session, name="WS", session_id="session-1"
    )
    doc = doc_svc.create_document(
        db_session,
        workspace_id=ws.id,
        file_name="a.pdf",
        file_format="pdf",
        file_size=1,
        file_path=None,
    )

    with patch(
        "app.services.document.delete_document_chunks",
        side_effect=RuntimeError("qdrant down"),
    ):
        deleted, diagnostic = doc_svc.delete_document(
            db_session, doc.id
        )

    # The deletion is aborted and can be retried.
    assert deleted is False
    assert "vector cleanup failed" in diagnostic
    assert doc_svc.get_document(db_session, doc.id) is not None


def test_delete_document_reports_file_cleanup_failure(
    db_session, monkeypatch
):
    from unittest.mock import patch

    from app.services.file_storage import UPLOAD_DIR

    doc_svc = DocumentService()
    ws_svc = WorkspaceService()

    ws = ws_svc.create_workspace(
        db_session, name="WS", session_id="session-1"
    )
    doc = doc_svc.create_document(
        db_session,
        workspace_id=ws.id,
        file_name="a.pdf",
        file_format="pdf",
        file_size=1,
        file_path=str(UPLOAD_DIR / "stored-a.pdf"),
    )

    with patch(
        "app.services.document.delete_document_chunks"
    ), patch(
        "pathlib.Path.unlink", side_effect=OSError("disk")
    ):
        deleted, diagnostic = doc_svc.delete_document(
            db_session, doc.id
        )

    # The record is gone; the file cleanup failure is
    # reported instead of claiming complete deletion.
    assert deleted is True
    assert "file cleanup failed" in diagnostic
    assert doc_svc.get_document(db_session, doc.id) is None


def test_delete_missing_document(db_session):
    doc_svc = DocumentService()

    deleted, diagnostic = doc_svc.delete_document(
        db_session, 99999
    )

    assert deleted is False
    assert diagnostic is None
