from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.services.workspace import WorkspaceService
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse

router = APIRouter()
service = WorkspaceService()

@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(workspace_in: WorkspaceCreate, db: Session = Depends(get_db)):
    return service.create_workspace(db, name=workspace_in.name)

@router.get("/", response_model=List[WorkspaceResponse])
def read_workspaces(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return service.list_workspaces(db, skip=skip, limit=limit)

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def read_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace = service.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(workspace_id: int, workspace_in: WorkspaceUpdate, db: Session = Depends(get_db)):
    if workspace_in.name is None:
        workspace = service.get_workspace(db, workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace

    workspace = service.update_workspace(db, id=workspace_id, name=workspace_in.name)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(workspace_id: int, db: Session = Depends(get_db)):
    workspace, err = service.delete_workspace(db, id=workspace_id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Workspace not found")
    elif err == "conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete workspace with existing documents, conversations, or evaluation cases",
        )
    return None
