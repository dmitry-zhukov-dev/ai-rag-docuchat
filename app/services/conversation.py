
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models.conversation import Conversation
from app.db.models.message import Message
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.workspace import WorkspaceRepository


class ConversationService:
    def __init__(self):
        self.repo = ConversationRepository()
        self.msg_repo = MessageRepository()
        self.workspace_repo = WorkspaceRepository()

    def get_conversation(
        self,
        db: Session,
        id: int,
    ) -> Optional[Conversation]:
        return self.repo.get(db, id)

    def list_workspace_conversations(
        self,
        db: Session,
        workspace_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Optional[List[Conversation]]:
        if not self.workspace_repo.get(db, workspace_id):
            return None

        return self.repo.get_by_workspace(
            db,
            workspace_id=workspace_id,
            skip=skip,
            limit=limit,
        )

    def create_conversation(
        self,
        db: Session,
        workspace_id: int,
        title: Optional[str] = None,
    ) -> Optional[Conversation]:
        if not self.workspace_repo.get(db, workspace_id):
            return None

        return self.repo.create(
            db,
            workspace_id=workspace_id,
            title=title,
        )

    def list_messages(
        self,
        db: Session,
        conversation_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Optional[List[Message]]:
        if not self.repo.get(db, conversation_id):
            return None

        return self.msg_repo.get_by_conversation(
            db,
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
        )

    def add_message(
        self,
        db: Session,
        conversation_id: int,
        sender_role: str,
        text: str,
    ) -> Optional[Message]:
        if not self.repo.get(db, conversation_id):
            return None

        return self.msg_repo.create(
            db,
            conversation_id=conversation_id,
            sender_role=sender_role,
            text=text,
        )

    def delete_conversation(
        self,
        db: Session,
        conversation_id: int,
    ) -> bool:
        conversation = self.repo.get(db, conversation_id)

        if conversation is None:
            return False

        self.repo.delete(db, conversation_id)
        return True


    def update_conversation(
        self,
        db: Session,
        conversation_id: int,
        title: str,
    ) -> Optional[Conversation]:
        conversation = self.repo.get(db, conversation_id)

        if conversation is None:
            return None

        return self.repo.update(
            db,
            db_obj=conversation,
            title=title,
        )
