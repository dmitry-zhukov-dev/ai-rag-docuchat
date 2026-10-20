from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.models.message import Message

class MessageRepository:
    def get(self, db: Session, id: int) -> Optional[Message]:
        return db.get(Message, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[Message]:
        return db.query(Message).offset(skip).limit(limit).all()

    def get_by_conversation(
        self, db: Session, *, conversation_id: int, skip: int = 0, limit: int = 100
    ) -> List[Message]:
        return (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create(
        self,
        db: Session,
        *,
        conversation_id: int,
        sender_role: str,
        text: str,
        sources: Optional[list] = None,
    ) -> Message:
        db_obj = Message(
            conversation_id=conversation_id,
            sender_role=sender_role,
            text=text,
            sources=sources,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: Message, text: Optional[str] = None) -> Message:
        if text is not None:
            db_obj.text = text
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, id: int) -> Optional[Message]:
        obj = db.get(Message, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
