import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.services.evaluation import EvaluationService, RUN_COMPLETED, RUN_FAILED
from app.db.models.evaluation import EvaluationCase, EvaluationRun
from app.rag.generation import RAGAnswer

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def evaluation_service():
    service = EvaluationService()
    service.case_repo = MagicMock()
    service.run_repo = MagicMock()
    return service

def test_run_case_success(evaluation_service, mock_db):
    # Setup
    case = EvaluationCase(
        id=1, workspace_id=1, question="Test?",
        expected_sources=[{"document_id": "1", "page": 1}],
        required_facts=["fact1"]
    )
    evaluation_service.case_repo.get.return_value = case
    
    mock_run = EvaluationRun(id=10)
    evaluation_service.run_repo.create.return_value = mock_run
    
    rag_answer = RAGAnswer(
        answer="This is fact1.",
        insufficient_context=False,
        sources=[{"document_id": "1", "page": 1}],
        chunks=[],
    )
    
    with patch("app.services.evaluation.answer_question", return_value=rag_answer), \
         patch.object(evaluation_service, "_ready_document_ids", return_value=[]):
        
        # Execute
        evaluation_service.run_case(mock_db, 1)
        
        # Verify
        args, kwargs = evaluation_service.run_repo.update.call_args
        assert kwargs['status'] == RUN_COMPLETED
        assert kwargs['answer'] == "This is fact1."
        assert kwargs['actual_sources'] == [{"document_id": "1", "page": 1}]
        assert "fact_coverage" in kwargs['metrics']
        assert kwargs['metrics']['fact_coverage'] == 1.0

def test_run_case_failure(evaluation_service, mock_db):
    # Setup
    case = EvaluationCase(id=1, workspace_id=1, question="Test?")
    evaluation_service.case_repo.get.return_value = case
    
    mock_run = EvaluationRun(id=10)
    evaluation_service.run_repo.create.return_value = mock_run
    
    with patch("app.services.evaluation.answer_question", side_effect=ValueError("RAG failure")), \
         patch.object(evaluation_service, "_ready_document_ids", return_value=[]):
        
        # Execute
        evaluation_service.run_case(mock_db, 1)
        
        # Verify
        args, kwargs = evaluation_service.run_repo.update.call_args
        assert kwargs['status'] == RUN_FAILED
        assert kwargs['error'] == "RAG failure"

def test_run_case_empty_retrieval(evaluation_service, mock_db):
    # Setup
    case = EvaluationCase(
        id=1, workspace_id=1, question="Test?",
        expected_sources=[{"document_id": "1", "page": 1}]
    )
    evaluation_service.case_repo.get.return_value = case
    
    mock_run = EvaluationRun(id=10)
    evaluation_service.run_repo.create.return_value = mock_run
    
    rag_answer = RAGAnswer(
        answer="I don't know.",
        insufficient_context=True,
        sources=[], # Empty sources
        chunks=[],
    )
    
    with patch("app.services.evaluation.answer_question", return_value=rag_answer), \
         patch.object(evaluation_service, "_ready_document_ids", return_value=[]):
        
        # Execute
        evaluation_service.run_case(mock_db, 1)
        
        # Verify
        args, kwargs = evaluation_service.run_repo.update.call_args
        assert kwargs['status'] == RUN_COMPLETED
        assert kwargs['actual_sources'] == []
        assert kwargs['metrics']['retrieval_hit_rate'] == 0.0
