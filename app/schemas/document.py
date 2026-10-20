from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class DocumentBase(BaseModel):
    file_name: str = Field(..., max_length=255)
    file_format: str = Field(..., max_length=50)
    file_size: int = Field(..., ge=0)
    num_pages: Optional[int] = Field(None, ge=0)

class DocumentCreate(DocumentBase):
    # Metadata-only creation always starts in the
    # "processing" state; a ready status can only result
    # from completed processing, never from client input.
    pass

class DocumentUpdate(BaseModel):
    file_name: Optional[str] = Field(None, max_length=255)
    indexing_status: Optional[str] = Field(None, max_length=50)
    num_pages: Optional[int] = Field(None, ge=0)

class DocumentResponse(DocumentBase):
    id: int
    workspace_id: int
    conversation_id: Optional[int] = None
    file_hash: Optional[str] = None
    indexing_status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(DocumentResponse):
    disposition: str  # accepted, already_exists, processing, failed, retried
