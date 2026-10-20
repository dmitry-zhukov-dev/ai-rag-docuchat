from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.session import Session


class SessionRepository:
    def get(self, db: Session, session_id: str) -> Optional[Session]:
        return db.get(Session, session_id)

    def get_multi(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> List[Session]:
        return db.query(Session).offset(skip).limit(limit).all()

    def create(
        self, db: Session, *, session_id: str, expires_at: datetime
    ) -> Session:
        db_obj = Session(id=session_id, expires_at=expires_at)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, *, session_id: str) -> bool:
        obj = db.get(Session, session_id)
        if obj:
            db.delete(obj)
            db.commit()
            return True
        return False

    def delete_expired(self, db: Session, before: datetime) -> int:
        """Delete expired sessions. Returns the removed count."""
        deleted = (
            db.query(Session)
            .filter(Session.expires_at < before)
            .delete(synchronize_session=False)
        )
        db.commit()
        return deleted
