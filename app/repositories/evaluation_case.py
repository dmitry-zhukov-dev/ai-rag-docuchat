from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.evaluation import EvaluationCase

class EvaluationCaseRepository:
    def get(self, db: Session, id: int) -> Optional[EvaluationCase]:
        return db.get(EvaluationCase, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[EvaluationCase]:
        return db.query(EvaluationCase).offset(skip).limit(limit).all()

    def get_by_workspace(
        self, db: Session, *, workspace_id: int, skip: int = 0, limit: int = 100
    ) -> List[EvaluationCase]:
        return db.query(EvaluationCase).filter(EvaluationCase.workspace_id == workspace_id).offset(skip).limit(limit).all()

    def create(
        self,
        db: Session,
        *,
        workspace_id: int,
        name: str,
        question: str,
        reference_answer: Optional[str] = None,
        required_facts: Optional[list] = None,
        expected_sources: Optional[list] = None,
        selected_document_ids: Optional[list] = None,
    ) -> EvaluationCase:
        db_obj = EvaluationCase(
            workspace_id=workspace_id,
            name=name,
            question=question,
            reference_answer=reference_answer,
            required_facts=required_facts,
            expected_sources=expected_sources,
            selected_document_ids=selected_document_ids,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: EvaluationCase,
        name: Optional[str] = None,
        question: Optional[str] = None,
        reference_answer: Optional[str] = None,
        required_facts: Optional[list] = None,
        expected_sources: Optional[list] = None,
        selected_document_ids: Optional[list] = None,
    ) -> EvaluationCase:
        if name is not None:
            db_obj.name = name
        if question is not None:
            db_obj.question = question
        if reference_answer is not None:
            db_obj.reference_answer = reference_answer
        if required_facts is not None:
            db_obj.required_facts = required_facts
        if expected_sources is not None:
            db_obj.expected_sources = expected_sources
        if selected_document_ids is not None:
            db_obj.selected_document_ids = selected_document_ids
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> Optional[EvaluationCase]:
        obj = db.get(EvaluationCase, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
