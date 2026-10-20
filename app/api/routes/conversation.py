from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_current_session, get_db
from app.core import security
from app.core.security import SessionModel
from app.services.conversation import ConversationService
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)

workspace_conversations_router = APIRouter()
conversations_router = APIRouter()
service = ConversationService()

@workspace_conversations_router.post(
    "/workspaces/{workspace_id}/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    workspace_id: int,
    conversation_in: ConversationCreate,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)

    conv = service.create_conversation(
        db, workspace_id=workspace_id, title=conversation_in.title
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return conv

@workspace_conversations_router.get(
    "/workspaces/{workspace_id}/conversations",
    response_model=List[ConversationResponse],
)
def list_workspace_conversations(
    workspace_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)

    convs = service.list_workspace_conversations(
        db, workspace_id=workspace_id, skip=skip, limit=limit
    )
    if convs is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return convs

@conversations_router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
def read_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_conversation_access(db, session, conversation_id)

    conv = service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@conversations_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
)
def list_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_conversation_access(db, session, conversation_id)

    messages = service.list_messages(
        db, conversation_id=conversation_id, skip=skip, limit=limit
    )
    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return messages

@conversations_router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_message(
    conversation_id: int,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_conversation_access(db, session, conversation_id)

    msg = service.add_message(
        db,
        conversation_id=conversation_id,
        sender_role=message_in.sender_role,
        text=message_in.text,
    )
    if not msg:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return msg


@conversations_router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_conversation_access(db, session, conversation_id)

    deleted = service.delete_conversation(db, conversation_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return None


@conversations_router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
)
def update_conversation(
    conversation_id: int,
    conversation_in: ConversationUpdate,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_conversation_access(db, session, conversation_id)

    conversation = service.update_conversation(
        db,
        conversation_id=conversation_id,
        title=conversation_in.title,
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation
