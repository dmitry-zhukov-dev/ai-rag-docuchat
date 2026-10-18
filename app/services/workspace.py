
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.workspace import Workspace
from app.repositories.workspace import WorkspaceRepository
from app.services.document import DocumentService
from app.services.conversation import ConversationService
from app.repositories.evaluation_case import EvaluationCaseRepository

class WorkspaceService:
    def __init__(self):
        self.repo = WorkspaceRepository()
        self.document_service = DocumentService()
        self.conversation_service = ConversationService()

    def get_workspace(
        self,
        db: Session,
        id: int,
    ) -> Optional[Workspace]:
        return self.repo.get(db, id)

    def list_workspaces(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Workspace]:
        return self.repo.get_multi(db, skip=skip, limit=limit)

    def create_workspace(
        self,
        db: Session,
        name: str,
    ) -> Workspace:
        return self.repo.create(db, name=name)

    def update_workspace(
        self,
        db: Session,
        id: int,
        name: str,
    ) -> Optional[Workspace]:
        workspace = self.repo.get(db, id)

        if workspace is None:
            return None

        return self.repo.update(db, db_obj=workspace, name=name)

    def delete_workspace(
        self,
        db: Session,
        id: int,
    ) -> Tuple[Optional[Workspace], Optional[str]]:
        workspace = self.repo.get(db, id)

        if workspace is None:
            return None, "not_found"

        # Evaluation cases are not yet handled by this deletion flow.
        if workspace.evaluation_cases:
            return None, "conflict"

        # Delete documents through DocumentService so their Qdrant
        # vectors and stored files are cleaned up as well.
        document_ids = [document.id for document in workspace.documents]

        for document_id in document_ids:
            deleted = self.document_service.delete_document(db, document_id)

            if not deleted:
                return None, "conflict"

        # Delete conversations and their associated messages.
        conversation_ids = [
            conversation.id for conversation in workspace.conversations
        ]

        for conversation_id in conversation_ids:
            deleted = self.conversation_service.delete_conversation(
                db,
                conversation_id,
            )

            if not deleted:
                return None, "conflict"

        try:
            deleted_workspace = self.repo.delete(db, id=id)
            return deleted_workspace, None
        except IntegrityError:
            db.rollback()
            return None, "conflict"
