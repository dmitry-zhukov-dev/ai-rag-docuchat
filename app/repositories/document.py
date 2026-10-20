
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.db.models.conversation import Conversation

from app.db.models.document import Document


class DocumentRepository:
    def get(self, db: Session, id: int) -> Optional[Document]:
        return db.get(Document, id)

    def get_multi(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        return db.query(Document).offset(skip).limit(limit).all()

    def get_by_workspace(
        self,
        db: Session,
        *,
        workspace_id: int,
        indexing_status: Optional[str] = None,
        conversation_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        query = db.query(Document).filter(
            Document.workspace_id == workspace_id
        )

        if conversation_id is not None:
            query = query.filter(or_(Document.conversation_id == conversation_id, Document.conversation_id.is_(None)))

        if indexing_status:
            query = query.filter(
                Document.indexing_status == indexing_status
            )

        return query.order_by(Document.id).offset(skip).limit(limit).all()

    def create(
        self,
        db: Session,
        *,
        workspace_id: int,
        file_name: str,
        file_format: str,
        file_size: int,
        num_pages: Optional[int] = None,
        indexing_status: str = "processing",
        file_path: Optional[str] = None,
    ) -> Document:
        db_obj = Document(
            workspace_id=workspace_id,
            file_name=file_name,
            file_format=file_format,
            file_size=file_size,
            num_pages=num_pages,
            indexing_status=indexing_status,
            file_path=file_path,
        )

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: Document,
        file_name: Optional[str] = None,
        indexing_status: Optional[str] = None,
        num_pages: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Document:
        if file_name is not None:
            db_obj.file_name = file_name

        if indexing_status is not None:
            db_obj.indexing_status = indexing_status

        if num_pages is not None:
            db_obj.num_pages = num_pages

        if error_message is not None:
            db_obj.error_message = error_message

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        return db_obj

    def delete(
        self,
        db: Session,
        *,
        id: int,
    ) -> Optional[Document]:
        obj = db.get(Document, id)

        if obj:
            db.delete(obj)
            db.commit()

        return obj

    def claim_upload(self, db: Session, *, workspace_id: int, conversation_id: int,
                     file_hash: str, file_name: str, file_format: str,
                     file_size: int, file_path: str, retry: bool = False):
        """Serialize claims on the existing conversation row (PostgreSQL).

        Commit processing BEFORE ingestion. Other workers then return its status,
        never start another job. The unique constraint is a second line of defense.
        All new upload paths must use this method, including failed retries.
        """
        conversation = (db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
        ).with_for_update().first())
        if conversation is None:
            db.rollback()
            raise ValueError("Conversation not found.")
        doc = db.query(Document).filter(
            Document.conversation_id == conversation_id,
            Document.file_hash == file_hash,
        ).populate_existing().first()
        if doc is not None:
            if doc.indexing_status != "failed" or not retry:
                disposition = {"completed": "already_exists", "failed": "failed"}.get(
                    doc.indexing_status, "processing")
                db.commit()
                return doc, disposition, False
            doc.indexing_status = "processing"
            doc.error_message = None
            doc.file_path = file_path
            disposition = "retried"
        else:
            doc = Document(workspace_id=workspace_id, conversation_id=conversation_id,
                           file_hash=file_hash, file_name=file_name, file_format=file_format,
                           file_size=file_size, file_path=file_path, indexing_status="processing")
            db.add(doc)
            disposition = "accepted"
        db.commit()
        db.refresh(doc)
        return doc, disposition, True
