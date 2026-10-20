from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_current_session, get_db
from app.core import security
from app.core.security import SessionModel
from app.services.workspace import WorkspaceService
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse

router = APIRouter()
service = WorkspaceService()

@router.post("/", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    workspace_in: WorkspaceCreate,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    return service.create_workspace(
        db, name=workspace_in.name, session_id=session.id
    )

@router.get("/", response_model=List[WorkspaceResponse])
def read_workspaces(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    # Only the current session's workspaces are listed.
    return service.list_session_workspaces(
        db, session_id=session.id, skip=skip, limit=limit
    )

@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def read_workspace(
    workspace_id: int,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)
    workspace = service.get_workspace(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int,
    workspace_in: WorkspaceUpdate,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)

    if workspace_in.name is None:
        workspace = service.get_workspace(db, workspace_id)
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace

    workspace = service.update_workspace(db, id=workspace_id, name=workspace_in.name)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    response: Response,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)
    workspace, err, diagnostics = service.delete_workspace(db, id=workspace_id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail="Workspace not found")
    elif err == "conflict":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete workspace because related data could not be removed",
        )

    if not diagnostics:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    # The workspace was deleted, but some related
    # cleanup failed and is reported for diagnosis.
    return {"deleted": True, "diagnostics": diagnostics}
