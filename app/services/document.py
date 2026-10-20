
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.conversation import Conversation
from app.integrations.qdrant import delete_document_chunks
from app.repositories.document import DocumentRepository
from app.repositories.workspace import WorkspaceRepository
from app.services.file_storage import UPLOAD_DIR


class DocumentService:
    def __init__(self):
        self.repo = DocumentRepository()
        self.workspace_repo = WorkspaceRepository()

    def claim_upload(self, db: Session, **metadata):
        return self.repo.claim_upload(db, **metadata)

    def get_document(self, db: Session, id: int) -> Optional[Document]:
        return self.repo.get(db, id)

    def list_workspace_documents(
        self,
        db: Session,
        workspace_id: int,
        indexing_status: Optional[str] = None,
        conversation_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Optional[list[Document]]:
        if not self.workspace_repo.get(db, workspace_id):
            return None

        return self.repo.get_by_workspace(
            db,
            workspace_id=workspace_id,
            indexing_status=indexing_status,
            conversation_id=conversation_id,
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
        error_message: Optional[str] = None,
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
            error_message=error_message,
        )

    def delete_document(self, db: Session, id: int) -> tuple[bool, Optional[str]]:
        """Delete a document, its indexed chunks, and its stored file.

        Returns (deleted, diagnostic). The deletion is safe to
        repeat: a missing document reports (False, None). When
        cleanup partially fails, the operation reports a
        diagnostic instead of claiming complete deletion.
        """
        doc = self.repo.get(db, id)

        if doc is None:
            return False, None

        if doc.conversation_id is not None:
            db.query(Conversation).filter(Conversation.id == doc.conversation_id).with_for_update().first()
            db.refresh(doc)
            if doc.indexing_status == "processing":
                db.rollback()
                return False, "Document is still processing."

        stored_path = doc.file_path
        diagnostics: list[str] = []

        # Vector index first: if this fails, the database
        # record and stored file are kept so the deletion
        # can be safely retried.
        try:
            delete_document_chunks(str(doc.id))
        except Exception as exc:
            diagnostics.append(
                f"vector cleanup failed: {type(exc).__name__}"
            )
            return False, "; ".join(diagnostics)

        try:
            db.delete(doc)
            db.commit()
        except Exception:
            db.rollback()
            raise

        # Only delete files located inside the configured
        # uploads directory.
        if stored_path:
            upload_root = UPLOAD_DIR.resolve()
            file_path = Path(stored_path).resolve()

            try:
                file_path.relative_to(upload_root)
            except ValueError:
                # Never delete a path outside uploads.
                return True, None

            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                diagnostics.append("file cleanup failed")

        if diagnostics:
            return True, "; ".join(diagnostics)

        return True, None
