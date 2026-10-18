
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.integrations.qdrant import delete_document_chunks
from app.repositories.document import DocumentRepository
from app.repositories.workspace import WorkspaceRepository
from app.services.file_storage import UPLOAD_DIR


class DocumentService:
    def __init__(self):
        self.repo = DocumentRepository()
        self.workspace_repo = WorkspaceRepository()

    def get_document(self, db: Session, id: int) -> Optional[Document]:
        return self.repo.get(db, id)

    def list_workspace_documents(
        self,
        db: Session,
        workspace_id: int,
        indexing_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Optional[list[Document]]:
        if not self.workspace_repo.get(db, workspace_id):
            return None

        return self.repo.get_by_workspace(
            db,
            workspace_id=workspace_id,
            indexing_status=indexing_status,
            skip=skip,
            limit=limit,
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
        file_path: Optional[str] = None,
    ) -> Optional[Document]:
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
            file_path=file_path,
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

    def delete_document(self, db: Session, id: int) -> bool:
        """Delete a document, its indexed chunks, and its stored file."""
        doc = self.repo.get(db, id)

        if doc is None:
            return False

        stored_path = doc.file_path

        # If Qdrant fails, keep the database record and stored file.
        delete_document_chunks(str(doc.id))

        try:
            db.delete(doc)
            db.commit()
        except Exception:
            db.rollback()
            raise

        # Only delete files located inside the configured uploads directory.
        if stored_path:
            upload_root = UPLOAD_DIR.resolve()
            file_path = Path(stored_path).resolve()

            try:
                file_path.relative_to(upload_root)
            except ValueError:
                # Never delete a path outside uploads.
                return True

            file_path.unlink(missing_ok=True)

        return True
