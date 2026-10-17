from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.repositories.workspace import WorkspaceRepository
from app.db.models.workspace import Workspace
from typing import Optional, List, Tuple

class WorkspaceService:
    def __init__(self):
        self.repo = WorkspaceRepository()

    def get_workspace(self, db: Session, id: int) -> Optional[Workspace]:
        return self.repo.get(db, id)

    def list_workspaces(self, db: Session, skip: int = 0, limit: int = 100) -> List[Workspace]:
        return self.repo.get_multi(db, skip=skip, limit=limit)

    def create_workspace(self, db: Session, name: str) -> Workspace:
        return self.repo.create(db, name=name)

    def update_workspace(self, db: Session, id: int, name: str) -> Optional[Workspace]:
        ws = self.repo.get(db, id)
        if ws:
            return self.repo.update(db, db_obj=ws, name=name)
        return None

    def delete_workspace(self, db: Session, id: int) -> Tuple[Optional[Workspace], Optional[str]]:
        ws = self.repo.get(db, id)
        if not ws:
            return None, "not_found"
        
        # Check if workspace has dependent documents or conversations
        if ws.documents or ws.conversations or ws.evaluation_cases:
            return None, "conflict"

        try:
            deleted = self.repo.delete(db, id=id)
            return deleted, None
        except IntegrityError:
            db.rollback()
            return None, "conflict"
