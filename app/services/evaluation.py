from sqlalchemy.orm import Session
from app.repositories.evaluation_case import EvaluationCaseRepository
from app.repositories.evaluation_run import EvaluationRunRepository
from app.db.models.evaluation import EvaluationCase, EvaluationRun
from typing import Optional, List

class EvaluationService:
    def __init__(self):
        self.case_repo = EvaluationCaseRepository()
        self.run_repo = EvaluationRunRepository()

    def list_cases(self, db: Session, workspace_id: int) -> List[EvaluationCase]:
        return self.case_repo.get_by_workspace(db, workspace_id=workspace_id)

    def create_case(self, db: Session, workspace_id: int, name: str, question: str) -> EvaluationCase:
        return self.case_repo.create(db, workspace_id=workspace_id, name=name, question=question)

    def list_runs(self, db: Session, evaluation_case_id: int) -> List[EvaluationRun]:
        return self.run_repo.get_by_case(db, evaluation_case_id=evaluation_case_id)

    def create_run(self, db: Session, evaluation_case_id: int, result_text: str) -> EvaluationRun:
        return self.run_repo.create(db, evaluation_case_id=evaluation_case_id, result_text=result_text)
