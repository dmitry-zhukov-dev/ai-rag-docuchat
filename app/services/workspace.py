import logging
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.workspace import Workspace
from app.repositories.evaluation_case import EvaluationCaseRepository
from app.repositories.evaluation_run import EvaluationRunRepository
from app.repositories.workspace import WorkspaceRepository
from app.services.document import DocumentService
from app.services.conversation import ConversationService

logger = logging.getLogger(__name__)

class WorkspaceService:
    def __init__(self):
        self.repo = WorkspaceRepository()
        self.document_service = DocumentService()
        self.conversation_service = ConversationService()
        self.evaluation_case_repo = EvaluationCaseRepository()
        self.evaluation_run_repo = EvaluationRunRepository()

    def get_workspace(
        self,
        db: Session,
        id: int,
    ) -> Optional[Workspace]:
        return self.repo.get(db, id)

    def list_session_workspaces(
        self,
        db: Session,
        session_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Workspace]:
        return self.repo.get_by_session(
            db, session_id=session_id, skip=skip, limit=limit
        )

    def create_workspace(
        self,
        db: Session,
        name: str,
        session_id: str,
    ) -> Workspace:
        return self.repo.create(
            db, name=name, session_id=session_id
        )

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
        self, db: Session, id: int
    ) -> Tuple[Optional[Workspace], Optional[str], list[str]]:
        """Delete a workspace and all of its data.

        Related evaluation runs and cases, documents
        (including their vector points and files), and
        conversations (including messages) are removed.
        Partial cleanup failures are reported as
        diagnostics instead of blocking the deletion.
        """
        workspace = self.repo.get(db, id)

        if workspace is None:
            return None, "not_found", []

        diagnostics: list[str] = []

        # Evaluation data: runs before their cases.
        for case in list(workspace.evaluation_cases):
            for run in list(case.runs):
                try:
                    self.evaluation_run_repo.delete(
                        db, id=run.id
                    )
                except Exception as exc:
                    diagnostics.append(
                        f"evaluation run {run.id} cleanup"
                        f" failed: {type(exc).__name__}"
                    )

            try:
                self.evaluation_case_repo.delete(
                    db, id=case.id
                )
            except Exception as exc:
                diagnostics.append(
                    f"evaluation case {case.id} cleanup"
                    f" failed: {type(exc).__name__}"
                )

        # Documents through DocumentService so their
        # Qdrant vectors and stored files are cleaned up
        # as well.
        for document in list(workspace.documents):
            deleted, diagnostic = self.document_service.delete_document(
                db, document.id
            )

            if not deleted:
                diagnostics.append(
                    f"document {document.id} cleanup failed"
                    f"{': ' + diagnostic if diagnostic else ''}"
                )

        # Do not remove chats while a document remains (including processing uploads).
        if self.document_service.list_workspace_documents(db, workspace_id=id, limit=1):
            db.rollback()
            return None, "conflict", diagnostics

        # Conversations cascade to their messages.
        for conversation in list(workspace.conversations):
            try:
                deleted = self.conversation_service.delete_conversation(db, conversation.id)
            except ValueError:
                db.rollback()
                return None, "conflict", diagnostics

            if not deleted:
                diagnostics.append(
                    f"conversation {conversation.id} cleanup failed"
                )

        try:
            deleted_workspace = self.repo.delete(db, id=id)
        except IntegrityError:
            db.rollback()
            return None, "conflict", diagnostics

        return deleted_workspace, None, diagnostics
