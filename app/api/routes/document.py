
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse
from app.services.document import DocumentService
from app.services.file_storage import save_uploaded_file
from app.rag.ingestion import ingest_document

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return doc


@documents_router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
):
    deleted = service.delete_document(db, document_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return None



@workspace_documents_router.post(
    "/workspaces/{workspace_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    workspace_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    file_name = file.filename

    try:
        saved_path = await save_uploaded_file(file)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    finally:
        await file.close()

    try:
        doc = service.create_document(
            db,
            workspace_id=workspace_id,
            file_name=file_name or saved_path.name,
            file_format=saved_path.suffix.lstrip(".").lower(),
            file_size=saved_path.stat().st_size,
            indexing_status="processing",
            file_path=str(saved_path.resolve()),
        )

        if doc is None:
            saved_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        try:
            ingest_document(
                file_path=str(saved_path),
                document_id=str(doc.id),
            )
        except Exception:
            service.update_document(
                db,
                id=doc.id,
                indexing_status="failed",
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Document indexing failed",
            )

        updated_doc = service.update_document(
            db,
            id=doc.id,
            indexing_status="completed",
        )

        return updated_doc

    except HTTPException:
        raise
    except Exception:
        saved_path.unlink(missing_ok=True)
        raise
