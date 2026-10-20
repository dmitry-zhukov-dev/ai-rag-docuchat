from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_db
from app.core import security
from app.core.security import SessionModel
from app.integrations.llm import GenerationError
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import ChatService

router = APIRouter()
service = ChatService()


@router.post(
    "/conversations/{conversation_id}/chat",
    response_model=ChatResponse,
)
def send_chat_message(
    conversation_id: int,
    chat_in: ChatRequest,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_conversation_access(db, session, conversation_id)

    try:
        return service.send_message(
            db=db,
            conversation_id=conversation_id,
            question=chat_in.question,
            limit=chat_in.limit,
            document_ids=chat_in.document_ids,
        )
    except ValueError as exc:
        detail = str(exc)

        if detail == "Conversation not found.":
            raise HTTPException(status_code=404, detail=detail) from exc

        if detail == "No indexed documents found in this workspace.":
            raise HTTPException(status_code=409, detail=detail) from exc

        if detail == "Invalid document selection.":
            raise HTTPException(status_code=400, detail=detail) from exc

        raise
    except GenerationError as exc:
        # The provider failed; no answer was produced, so no
        # fictitious success is persisted or returned.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
