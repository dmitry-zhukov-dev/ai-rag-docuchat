import logging
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.deps import get_current_session, get_db
from app.core import security
from app.core.security import SessionModel
from app.integrations.qdrant import delete_document_chunks
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse
from app.services.document import DocumentService
from app.services.file_storage import save_uploaded_file
from app.rag.ingestion import ingest_document

logger = logging.getLogger(__name__)

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
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)

    # Metadata-only creation always starts as
    # "processing": a client cannot fabricate a ready
    # document that was never indexed.
    doc = service.create_document(
        db,
        workspace_id=workspace_id,
        file_name=document_in.file_name,
        file_format=document_in.file_format,
        file_size=document_in.file_size,
        num_pages=document_in.num_pages,
        indexing_status="processing",
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
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)

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
    session: SessionModel = Depends(get_current_session),
):
    security.require_document_access(db, session, document_id)

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
    session: SessionModel = Depends(get_current_session),
):
    security.require_document_access(db, session, document_id)

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


@documents_router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    response: Response,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_document_access(db, session, document_id)

    deleted, diagnostic = service.delete_document(db, document_id)

    if not deleted and diagnostic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if not deleted:
        # Cleanup failed before the record was removed;
        # the deletion can be safely retried.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document deletion incomplete: {diagnostic}",
        )

    if diagnostic is None:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    # Partial cleanup: report it instead of claiming
    # complete deletion.
    return {"deleted": True, "diagnostic": diagnostic}


@workspace_documents_router.post(
    "/workspaces/{workspace_id}/documents/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    workspace_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)

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
                workspace_id=str(workspace_id),
                filename=doc.file_name,
            )
        except Exception as exc:
            # Compensate the failed indexing operation:
            # remove any partially indexed vector points
            # and the stored file, and keep a diagnosable
            # failed record without secrets.
            try:
                delete_document_chunks(str(doc.id))
            except Exception as cleanup_exc:
                logger.warning(
                    "Partial cleanup failed for document %s: %s",
                    doc.id,
                    type(cleanup_exc).__name__,
                )

            saved_path.unlink(missing_ok=True)

            service.update_document(
                db,
                id=doc.id,
                indexing_status="failed",
                error_message=f"indexing failed: {type(exc).__name__}",
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
