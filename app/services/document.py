from sqlalchemy.orm import Session
from app.repositories.document import DocumentRepository
from app.repositories.workspace import WorkspaceRepository
from app.db.models.document import Document
from typing import Optional, List

class DocumentService:
    def __init__(self):
        self.repo = DocumentRepository()
        self.workspace_repo = WorkspaceRepository()

    def get_document(self, db: Session, id: int) -> Optional[Document]:
        return self.repo.get(db, id)

    def list_workspace_documents(
        self, db: Session, workspace_id: int, indexing_status: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> Optional[List[Document]]:
        # Check workspace exists
        if not self.workspace_repo.get(db, workspace_id):
            return None
        return self.repo.get_by_workspace(
            db, workspace_id=workspace_id, indexing_status=indexing_status, skip=skip, limit=limit
        )

    def create_document(
        self,
        db: Session,
        workspace_id: int,
        file_name: str,
        file_format: str,
        file_size: int,
        num_pages: Optional[int] = None,
        indexing_status: str = "processing",
    ) -> Optional[Document]:
        # Check workspace exists
        if not self.workspace_repo.get(db, workspace_id):
            return None
        return self.repo.create(
            db,
            workspace_id=workspace_id,
            file_name=file_name,
            file_format=file_format,
            file_size=file_size,
            num_pages=num_pages,
            indexing_status=indexing_status,
        )

    def update_document(
        self,
        db: Session,
        id: int,
        file_name: Optional[str] = None,
        indexing_status: Optional[str] = None,
        num_pages: Optional[int] = None,
    ) -> Optional[Document]:
        doc = self.repo.get(db, id)
        if not doc:
            return None
        return self.repo.update(
            db,
            db_obj=doc,
            file_name=file_name,
            indexing_status=indexing_status,
            num_pages=num_pages,
        )
