from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.workspace import Workspace

class WorkspaceRepository:
    def get(self, db: Session, id: int) -> Optional[Workspace]:
        return db.get(Workspace, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Workspace]:
        return db.query(Workspace).offset(skip).limit(limit).all()

    def create(self, db: Session, *, name: str) -> Workspace:
        db_obj = Workspace(name=name)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Workspace, name: str) -> Workspace:
        db_obj.name = name
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> Optional[Workspace]:
        obj = db.get(Workspace, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
