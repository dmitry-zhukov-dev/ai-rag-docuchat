from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, List

class ConversationBase(BaseModel):
    title: Optional[str] = Field(None, max_length=255)

class ConversationCreate(ConversationBase):
    pass

class ConversationResponse(ConversationBase):
    id: int
    workspace_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MessageBase(BaseModel):
    sender_role: str = Field(..., max_length=50)
    text: str = Field(..., min_length=1)

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
