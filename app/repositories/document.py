
from typing import List, Optional

from sqlalchemy.orm import Session

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
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        query = db.query(Document).filter(
            Document.workspace_id == workspace_id
        )

        if indexing_status:
            query = query.filter(
                Document.indexing_status == indexing_status
            )

        return query.offset(skip).limit(limit).all()

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
    ) -> Document:
        if file_name is not None:
            db_obj.file_name = file_name

        if indexing_status is not None:
            db_obj.indexing_status = indexing_status

        if num_pages is not None:
            db_obj.num_pages = num_pages

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
