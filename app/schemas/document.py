from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class DocumentBase(BaseModel):
    file_name: str = Field(..., max_length=255)
    file_format: str = Field(..., max_length=50)
    file_size: int = Field(..., ge=0)
    num_pages: Optional[int] = Field(None, ge=0)

class DocumentCreate(DocumentBase):
    indexing_status: Optional[str] = Field("processing", max_length=50)

class DocumentUpdate(BaseModel):
    file_name: Optional[str] = Field(None, max_length=255)
    indexing_status: Optional[str] = Field(None, max_length=50)
    num_pages: Optional[int] = Field(None, ge=0)

class DocumentResponse(DocumentBase):
    id: int
    workspace_id: int
    indexing_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
