from pydantic import BaseModel, ConfigDict, Field, field_validator
from datetime import datetime
from typing import Optional

class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Workspace name cannot be empty or whitespace-only")
        return stripped

class WorkspaceCreate(WorkspaceBase):
    pass

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def validate_name_not_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        stripped = v.strip()
        if not stripped:
            raise ValueError("Workspace name cannot be empty or whitespace-only")
        return stripped

class WorkspaceResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
