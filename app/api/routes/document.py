import logging
import hashlib
from starlette.concurrency import run_in_threadpool
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
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse, DocumentUploadResponse
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
    conversation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)

    if conversation_id is not None:
        conversation = security.require_conversation_access(db, session, conversation_id)
        if conversation.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Conversation not found.")

    docs = service.list_workspace_documents(
        db,
        workspace_id=workspace_id,
        indexing_status=indexing_status,
        conversation_id=conversation_id,
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

    if document_in.indexing_status is not None:
        raise HTTPException(status_code=400, detail="Indexing status is managed by the server.")

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
    document = security.require_document_access(db, session, document_id)
    if document.conversation_id is not None and document.indexing_status == "processing":
        raise HTTPException(status_code=409, detail="Document is still processing.")

    deleted, diagnostic = service.delete_document(db, document_id)

    if not deleted and diagnostic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if not deleted and diagnostic == "Document is still processing.":
        raise HTTPException(status_code=409, detail=diagnostic)

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
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    workspace_id: int,
    response: Response,
    conversation_id: int = Query(..., ge=1),
    retry: bool = Query(False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)
    conversation = security.require_conversation_access(db, session, conversation_id)
    if conversation.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    file_name = file.filename
    if file_name and len(file_name) > 255:
        raise HTTPException(status_code=400, detail="Filename is too long.")
    try:
        saved_path = await save_uploaded_file(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()

    # Hash bytes exactly once; filenames never determine identity.
    try:
        file_hash = hashlib.sha256(saved_path.read_bytes()).hexdigest()
        doc, disposition, claimed = service.claim_upload(
            db, workspace_id=workspace_id, conversation_id=conversation_id,
            file_hash=file_hash, file_name=file_name or saved_path.name,
            file_format=saved_path.suffix.lstrip(".").lower(),
            file_size=saved_path.stat().st_size, file_path=str(saved_path.resolve()), retry=retry,
        )
    except Exception:
        db.rollback()
        saved_path.unlink(missing_ok=True)
        raise

    if not claimed:
        saved_path.unlink(missing_ok=True)
        response.status_code = 200
    else:
        # Only the worker that committed the claim may ingest. Offload the
        # unchanged synchronous pipeline so status requests can be served.
        try:
            if disposition == "retried":
                await run_in_threadpool(delete_document_chunks, str(doc.id))
            await run_in_threadpool(
                ingest_document, file_path=str(saved_path), document_id=str(doc.id),
                workspace_id=str(workspace_id), filename=doc.file_name,
            )
        except Exception as exc:
            try:
                await run_in_threadpool(delete_document_chunks, str(doc.id))
            except Exception:
                logger.warning("Partial vector cleanup failed for document %s", doc.id)
            saved_path.unlink(missing_ok=True)
            service.update_document(db, id=doc.id, indexing_status="failed",
                                    error_message="Indexing failed; select the same file to retry.")
            raise HTTPException(status_code=500, detail="Document indexing failed. Select the same file to retry.") from exc
        doc = service.update_document(db, id=doc.id, indexing_status="completed")

    return {**DocumentResponse.model_validate(doc).model_dump(), "disposition": disposition}
