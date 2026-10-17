from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.conversation import Conversation

class ConversationRepository:
    def get(self, db: Session, id: int) -> Optional[Conversation]:
        return db.get(Conversation, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Conversation]:
        return db.query(Conversation).offset(skip).limit(limit).all()

    def get_by_workspace(
        self, db: Session, *, workspace_id: int, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        return db.query(Conversation).filter(Conversation.workspace_id == workspace_id).offset(skip).limit(limit).all()

    def create(self, db: Session, *, workspace_id: int, title: Optional[str] = None) -> Conversation:
        db_obj = Conversation(workspace_id=workspace_id, title=title)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Conversation, title: Optional[str] = None) -> Conversation:
        if title is not None:
            db_obj.title = title
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> Optional[Conversation]:
        obj = db.get(Conversation, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
