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
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(
        self,
        db: Session,
        *,
        evaluation_case_id: int,
        config: Optional[dict] = None,
        result_text: Optional[str] = None,
        metrics: Optional[dict] = None
    ) -> EvaluationRun:
        db_obj = EvaluationRun(
            evaluation_case_id=evaluation_case_id, config=config, result_text=result_text, metrics=metrics
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
        result_text: Optional[str] = None,
        metrics: Optional[dict] = None
    ) -> EvaluationRun:
        if result_text is not None:
            db_obj.result_text = result_text
        if metrics is not None:
            db_obj.metrics = metrics
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
