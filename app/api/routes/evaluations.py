from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_current_session, get_db
from app.core import security
from app.core.security import SessionModel
from app.schemas.evaluation import (
    EvaluationCaseCreate,
    EvaluationCaseResponse,
    EvaluationCaseUpdate,
    EvaluationRunResponse,
)
from app.services.evaluation import EvaluationService

router = APIRouter()
service = EvaluationService()


@router.post(
    "/workspaces/{workspace_id}/evaluations",
    response_model=EvaluationCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation_case(
    workspace_id: int,
    case_in: EvaluationCaseCreate,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)

    return service.create_case(
        db,
        workspace_id=workspace_id,
        name=case_in.name,
        question=case_in.question,
        reference_answer=case_in.reference_answer,
        required_facts=case_in.required_facts,
        expected_sources=[
            source.model_dump()
            for source in (case_in.expected_sources or [])
        ],
        selected_document_ids=case_in.selected_document_ids,
    )


@router.get(
    "/workspaces/{workspace_id}/evaluations",
    response_model=List[EvaluationCaseResponse],
)
def list_evaluation_cases(
    workspace_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_workspace_access(db, session, workspace_id)

    return service.list_cases(db, workspace_id=workspace_id)


@router.get(
    "/evaluations/{case_id}",
    response_model=EvaluationCaseResponse,
)
def read_evaluation_case(
    case_id: int,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_evaluation_case_access(
        db, session, case_id
    )

    case = service.get_case(db, case_id)
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation case not found",
        )

    return case


@router.patch(
    "/evaluations/{case_id}",
    response_model=EvaluationCaseResponse,
)
def update_evaluation_case(
    case_id: int,
    case_in: EvaluationCaseUpdate,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_evaluation_case_access(
        db, session, case_id
    )

    updated = service.update_case(
        db,
        case_id=case_id,
        name=case_in.name,
        question=case_in.question,
        reference_answer=case_in.reference_answer,
        required_facts=case_in.required_facts,
        expected_sources=[
            source.model_dump()
            for source in (case_in.expected_sources or [])
        ]
        if case_in.expected_sources is not None
        else None,
        selected_document_ids=case_in.selected_document_ids,
    )

    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation case not found",
        )

    return updated


@router.delete(
    "/evaluations/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_evaluation_case(
    case_id: int,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_evaluation_case_access(
        db, session, case_id
    )

    if not service.delete_case(db, case_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation case not found",
        )

    return None


@router.post(
    "/evaluations/{case_id}/runs",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def run_evaluation_case(
    case_id: int,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_evaluation_case_access(
        db, session, case_id
    )

    return service.run_case(db, case_id)


@router.get(
    "/evaluations/{case_id}/runs",
    response_model=List[EvaluationRunResponse],
)
def list_evaluation_runs(
    case_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_evaluation_case_access(
        db, session, case_id
    )

    return service.list_runs(db, evaluation_case_id=case_id)


@router.get(
    "/evaluation-runs/{run_id}",
    response_model=EvaluationRunResponse,
)
def read_evaluation_run(
    run_id: int,
    db: Session = Depends(get_db),
    session: SessionModel = Depends(get_current_session),
):
    security.require_evaluation_run_access(db, session, run_id)

    return service.get_run(db, run_id)
