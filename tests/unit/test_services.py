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
    ws = ws_svc.create_workspace(db_session, name="WS1")
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
    run = eval_svc.create_run(db_session, evaluation_case_id=case.id, result_text="ok")
    assert len(eval_svc.list_runs(db_session, case.id)) == 1
