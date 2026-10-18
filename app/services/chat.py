
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
    ) -> dict:
        conversation = self.conversation_repo.get(db, conversation_id)

        if conversation is None:
            raise ValueError("Conversation not found.")

        documents = (
            db.query(Document.id)
            .filter(
                Document.workspace_id == conversation.workspace_id,
                Document.indexing_status == "completed",
            )
            .all()
        )

        document_ids = [str(document_id) for (document_id,) in documents]

        if not document_ids:
            raise ValueError(
                "No indexed documents found in this workspace."
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
        answer = answer_question(
            question=question,
            limit=limit,
            document_ids=document_ids,
            history=history,
        )

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
            text=answer,
        )

        return {
            "conversation_id": conversation_id,
            "question": question,
            "answer": answer,
        }
