
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
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
):
    try:
        return service.send_message(
            db=db,
            conversation_id=conversation_id,
            question=chat_in.question,
            limit=chat_in.limit,
        )
    except ValueError as exc:
        detail = str(exc)

        if detail == "Conversation not found.":
            raise HTTPException(status_code=404, detail=detail) from exc

        if detail == "No indexed documents found in this workspace.":
            raise HTTPException(status_code=409, detail=detail) from exc

        raise
