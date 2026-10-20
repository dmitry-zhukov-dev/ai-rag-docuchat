from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.evaluation import EvaluationRun

class EvaluationRunRepository:
    def get(self, db: Session, id: int) -> Optional[EvaluationRun]:
        return db.get(EvaluationRun, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[EvaluationRun]:
        return db.query(EvaluationRun).offset(skip).limit(limit).all()

    def get_by_case(
        self, db: Session, *, evaluation_case_id: int, skip: int = 0, limit: int = 100
    ) -> List[EvaluationRun]:
        return (
            db.query(EvaluationRun)
            .filter(EvaluationRun.evaluation_case_id == evaluation_case_id)
            .order_by(EvaluationRun.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(
        self,
        db: Session,
        *,
        evaluation_case_id: int,
        status: str = "pending",
    ) -> EvaluationRun:
        db_obj = EvaluationRun(
            evaluation_case_id=evaluation_case_id,
            status=status,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: EvaluationRun,
        status: Optional[str] = None,
        answer: Optional[str] = None,
        actual_sources: Optional[list] = None,
        metrics: Optional[dict] = None,
        error: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> EvaluationRun:
        if status is not None:
            db_obj.status = status
        if answer is not None:
            db_obj.answer = answer
        if actual_sources is not None:
            db_obj.actual_sources = actual_sources
        if metrics is not None:
            db_obj.metrics = metrics
        if error is not None:
            db_obj.error = error
        if completed_at is not None:
            db_obj.completed_at = completed_at
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> Optional[EvaluationRun]:
        obj = db.get(EvaluationRun, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
