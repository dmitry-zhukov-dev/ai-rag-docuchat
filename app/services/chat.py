from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.rag.generation import answer_question
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository


class ChatService:
    def __init__(self):
        self.conversation_repo = ConversationRepository()
        self.message_repo = MessageRepository()

    def send_message(
        self,
        db: Session,
        conversation_id: int,
        question: str,
        limit: int = 5,
        document_ids: Optional[list[int]] = None,
    ) -> dict:
        conversation = self.conversation_repo.get(db, conversation_id)

        if conversation is None:
            raise ValueError("Conversation not found.")

        if document_ids is None:
            # Omitted: search all ready documents in the
            # conversation's workspace.
            documents = (
                db.query(Document.id)
                .filter(
                    Document.workspace_id
                    == conversation.workspace_id,
                    Document.indexing_status == "completed",
                )
                .all()
            )

            selected_document_ids = [
                str(document_id) for (document_id,) in documents
            ]

            if not selected_document_ids:
                raise ValueError(
                    "No indexed documents found in this workspace."
                )
        elif not document_ids:
            # An explicitly empty selection searches no
            # documents and yields an insufficient-context
            # answer; it is never treated as unrestricted.
            selected_document_ids = []
        else:
            selected_document_ids = self._verify_selected_documents(
                db,
                workspace_id=conversation.workspace_id,
                document_ids=document_ids,
            )

        previous_messages = self.message_repo.get_by_conversation(
            db,
            conversation_id=conversation_id,
            skip=0,
            limit=100,
        )

        history = [
            {
                "sender_role": message.sender_role,
                "text": message.text,
            }
            for message in previous_messages
            if message.sender_role in ("user", "assistant")
        ]

        # Generate the answer before saving the new messages.
        # The workspace identifier scopes retrieval to this
        # workspace on the Qdrant side, and the accessible
        # document identifiers verify every retrieved chunk at
        # the application level.
        result = answer_question(
            question=question,
            workspace_id=str(conversation.workspace_id),
            limit=limit,
            document_ids=selected_document_ids,
            history=history,
            accessible_document_ids=set(selected_document_ids),
        )

        # The question is persisted before generation so
        # that a failed generation never fabricates an
        # answer and never loses the user's question.
        self.message_repo.create(
            db,
            conversation_id=conversation_id,
            sender_role="user",
            text=question,
        )

        self.message_repo.create(
            db,
            conversation_id=conversation_id,
            sender_role="assistant",
            text=result.answer,
            sources=result.sources,
        )

        return {
            "conversation_id": conversation_id,
            "question": question,
            "answer": result.answer,
            "insufficient_context": result.insufficient_context,
            "sources": result.sources,
        }

    def _verify_selected_documents(
        self,
        db: Session,
        workspace_id: int,
        document_ids: list[int],
    ) -> list[str]:
        """Verify ownership and readiness of selected documents.

        Only documents that exist in the conversation's
        workspace and are fully indexed may be searched.
        """
        unique_ids = set(document_ids)

        # Duplicate identifiers are rejected.
        if len(unique_ids) != len(document_ids):
            raise ValueError("Invalid document selection.")

        documents = (
            db.query(Document)
            .filter(
                Document.workspace_id == workspace_id,
                Document.id.in_(unique_ids),
            )
            .all()
        )

        # Unknown or foreign identifiers are rejected.
        if len(documents) != len(unique_ids):
            raise ValueError("Invalid document selection.")

        for document in documents:
            # Unready documents must not be searched.
            if document.indexing_status != "completed":
                raise ValueError("Invalid document selection.")

        return [str(document.id) for document in documents]
