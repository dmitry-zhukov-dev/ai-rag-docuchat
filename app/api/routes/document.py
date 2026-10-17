from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.api.deps import get_db
from app.services.document import DocumentService
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse

workspace_documents_router = APIRouter()
documents_router = APIRouter()
service = DocumentService()

@workspace_documents_router.post(
    "/workspaces/{workspace_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document(
    workspace_id: int,
    document_in: DocumentCreate,
    db: Session = Depends(get_db),
):
    doc = service.create_document(
        db,
        workspace_id=workspace_id,
        file_name=document_in.file_name,
        file_format=document_in.file_format,
        file_size=document_in.file_size,
        num_pages=document_in.num_pages,
        indexing_status=document_in.indexing_status or "processing",
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return doc

@workspace_documents_router.get(
    "/workspaces/{workspace_id}/documents",
    response_model=List[DocumentResponse],
)
def list_workspace_documents(
    workspace_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    indexing_status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    docs = service.list_workspace_documents(
        db,
        workspace_id=workspace_id,
        indexing_status=indexing_status,
        skip=skip,
        limit=limit,
    )
    if docs is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return docs

@documents_router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
def read_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    doc = service.get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@documents_router.patch(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
def update_document(
    document_id: int,
    document_in: DocumentUpdate,
    db: Session = Depends(get_db),
):
    doc = service.update_document(
        db,
        id=document_id,
        file_name=document_in.file_name,
        indexing_status=document_in.indexing_status,
        num_pages=document_in.num_pages,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
