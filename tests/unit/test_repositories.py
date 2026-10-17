import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.repositories.workspace import WorkspaceRepository
from app.repositories.document import DocumentRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.evaluation_case import EvaluationCaseRepository
from app.repositories.evaluation_run import EvaluationRunRepository

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)

def test_repositories(db_session):
    # Setup
    workspace_repo = WorkspaceRepository()
    doc_repo = DocumentRepository()
    conv_repo = ConversationRepository()
    msg_repo = MessageRepository()
    case_repo = EvaluationCaseRepository()
    run_repo = EvaluationRunRepository()

    ws = workspace_repo.create(db_session, name="WS1")

    # Document
    doc = doc_repo.create(db_session, workspace_id=ws.id, file_name="test.pdf", file_format="pdf", file_size=1024)
    assert doc_repo.get_by_workspace(db_session, workspace_id=ws.id)[0].id == doc.id
    doc_repo.update(db_session, db_obj=doc, indexing_status="completed")
    assert doc.indexing_status == "completed"

    # Conversation
    conv = conv_repo.create(db_session, workspace_id=ws.id, title="Conv1")
    assert conv_repo.get_by_workspace(db_session, workspace_id=ws.id)[0].id == conv.id

    # Message
    msg = msg_repo.create(db_session, conversation_id=conv.id, sender_role="user", text="hello")
    assert msg_repo.get_by_conversation(db_session, conversation_id=conv.id)[0].id == msg.id

    # EvaluationCase
    case = case_repo.create(db_session, workspace_id=ws.id, name="Case1", question="Q?")
    assert case_repo.get_by_workspace(db_session, workspace_id=ws.id)[0].id == case.id

    # EvaluationRun
    run = run_repo.create(db_session, evaluation_case_id=case.id, result_text="pass")
    assert run_repo.get_by_case(db_session, evaluation_case_id=case.id)[0].id == run.id

    # Delete test (cascade not configured, manually delete children first)
    run_repo.delete(db_session, id=run.id)
    msg_repo.delete(db_session, id=msg.id)
    conv_repo.delete(db_session, id=conv.id)
    doc_repo.delete(db_session, id=doc.id)
    case_repo.delete(db_session, id=case.id)
    
    workspace_repo.delete(db_session, id=ws.id)
    assert workspace_repo.get(db_session, ws.id) is None
