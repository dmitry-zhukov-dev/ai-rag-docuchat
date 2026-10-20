"""Evaluation mode: run the real RAG pipeline against
test cases and compute deterministic quality metrics."""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models.document import Document
from app.db.models.evaluation import EvaluationCase, EvaluationRun
from app.integrations.llm import GenerationError
from app.rag.generation import RAGAnswer, answer_question
from app.repositories.evaluation_case import EvaluationCaseRepository
from app.repositories.evaluation_run import EvaluationRunRepository

logger = logging.getLogger(__name__)

RUN_PENDING = "pending"
RUN_RUNNING = "running"
RUN_COMPLETED = "completed"
RUN_FAILED = "failed"


def _normalize(text: str) -> list[str]:
    """Return the alphanumeric tokens of a text.

    Common English possessives ("document's") are normalized so
    that the possessive-stripped form is also present, allowing
    a required fact such as "The Document's Title!" to match an
    answer that contains "document" without "document's".
    """
    tokens = re.findall(r"[a-z0-9']+", text.lower())
    normalized: list[str] = []
    for token in tokens:
        normalized.append(token)
        if token.endswith("'s") and len(token) > 2:
            normalized.append(token[:-2])
        elif token.endswith("'") and len(token) > 1:
            normalized.append(token[:-1])
    return normalized


def _fact_covered(fact: str, answer_tokens: list[str]) -> bool:
    """Check whether every token of a fact appears in the answer.

    This is a deterministic containment check for
    formalizable key facts, not a universal quality
    score.
    """
    fact_tokens = _normalize(fact)
    if not fact_tokens:
        return False
    
    # Check each token or its base form (without possessive 's)
    for token in fact_tokens:
        found = False
        candidates = {token}
        if token.endswith("'s") and len(token) > 2:
            candidates.add(token[:-2])
        elif token.endswith("'") and len(token) > 1:
            candidates.add(token[:-1])
        
        if any(c in answer_tokens for c in candidates):
            found = True
            
        if not found:
            return False
            
    return True


def _source_matches(
    expected: dict, actual: dict
) -> bool:
    """Compare an expected source with an actual one."""
    if str(expected.get("document_id")) != str(
        actual.get("document_id")
    ):
        return False

    expected_page = expected.get("page")
    if expected_page is not None and (
        actual.get("page") != expected_page
    ):
        return False

    return True


def compute_metrics(
    case: EvaluationCase,
    answer: str,
    actual_sources: list[dict],
) -> dict:
    """Compute deterministic evaluation metrics.

    Retrieval metrics compare the expected sources with
    the sources actually retrieved. Answer metrics check
    whether the required facts are covered by the
    actual answer. All metrics are explainable and
    reproducible.
    """
    metrics: dict = {}

    expected_sources = case.expected_sources or []
    if expected_sources:
        matched = 0
        unexpected = 0
        for actual in actual_sources:
            if any(
                _source_matches(expected, actual)
                for expected in expected_sources
            ):
                matched += 1
            else:
                unexpected += 1

        retrieved_expected = 0
        for expected in expected_sources:
            if any(
                _source_matches(expected, actual)
                for actual in actual_sources
            ):
                retrieved_expected += 1

        metrics["expected_sources_count"] = len(
            expected_sources
        )
        metrics["retrieved_expected_sources"] = (
            retrieved_expected
        )
        metrics["retrieval_hit_rate"] = (
            retrieved_expected / len(expected_sources)
        )
        metrics["unexpected_sources_count"] = unexpected
        if actual_sources:
            metrics["source_precision"] = (
                matched / len(actual_sources)
            )
        if expected_sources:
            metrics["source_recall"] = (
                retrieved_expected / len(expected_sources)
            )

    required_facts = case.required_facts or []
    if required_facts:
        answer_tokens = _normalize(answer)
        covered = [
            fact
            for fact in required_facts
            if _fact_covered(fact, answer_tokens)
        ]
        metrics["required_facts_count"] = len(required_facts)
        metrics["required_facts_covered"] = len(covered)
        metrics["fact_coverage"] = len(covered) / len(
            required_facts
        )

    return metrics


class EvaluationService:
    def __init__(self):
        self.case_repo = EvaluationCaseRepository()
        self.run_repo = EvaluationRunRepository()

    def list_cases(
        self, db: Session, workspace_id: int
    ) -> list[EvaluationCase]:
        return self.case_repo.get_by_workspace(
            db, workspace_id=workspace_id
        )

    def get_case(
        self, db: Session, case_id: int
    ) -> Optional[EvaluationCase]:
        return self.case_repo.get(db, case_id)

    def create_case(
        self,
        db: Session,
        workspace_id: int,
        name: str,
        question: str,
        reference_answer: Optional[str] = None,
        required_facts: Optional[list] = None,
        expected_sources: Optional[list] = None,
        selected_document_ids: Optional[list] = None,
    ) -> EvaluationCase:
        return self.case_repo.create(
            db,
            workspace_id=workspace_id,
            name=name,
            question=question,
            reference_answer=reference_answer,
            required_facts=required_facts,
            expected_sources=expected_sources,
            selected_document_ids=selected_document_ids,
        )

    def update_case(
        self,
        db: Session,
        case_id: int,
        name: Optional[str] = None,
        question: Optional[str] = None,
        reference_answer: Optional[str] = None,
        required_facts: Optional[list] = None,
        expected_sources: Optional[list] = None,
        selected_document_ids: Optional[list] = None,
    ) -> Optional[EvaluationCase]:
        case = self.case_repo.get(db, case_id)
        if case is None:
            return None

        return self.case_repo.update(
            db,
            db_obj=case,
            name=name,
            question=question,
            reference_answer=reference_answer,
            required_facts=required_facts,
            expected_sources=expected_sources,
            selected_document_ids=selected_document_ids,
        )

    def delete_case(
        self, db: Session, case_id: int
    ) -> bool:
        case = self.case_repo.get(db, case_id)
        if case is None:
            return False

        self.case_repo.delete(db, id=case_id)
        return True

    def list_runs(
        self, db: Session, evaluation_case_id: int
    ) -> list[EvaluationRun]:
        return self.run_repo.get_by_case(
            db, evaluation_case_id=evaluation_case_id
        )

    def get_run(
        self, db: Session, run_id: int
    ) -> Optional[EvaluationRun]:
        return self.run_repo.get(db, run_id)

    def run_case(
        self, db: Session, case_id: int
    ) -> EvaluationRun:
        """Execute the test case against the real RAG
        pipeline and persist the run with metrics."""
        case = self.case_repo.get(db, case_id)
        if case is None:
            raise ValueError("Evaluation case not found.")

        run = self.run_repo.create(
            db, evaluation_case_id=case_id, status=RUN_RUNNING
        )

        try:
            selected_document_ids = (
                case.selected_document_ids or []
            )

            if selected_document_ids:
                ready_ids = self._verify_selected_documents(
                    db, case.workspace_id, selected_document_ids
                )
            else:
                ready_ids = self._ready_document_ids(
                    db, case.workspace_id
                )

            result: RAGAnswer = answer_question(
                question=case.question,
                workspace_id=str(case.workspace_id),
                document_ids=[
                    str(document_id)
                    for document_id in ready_ids
                ],
                accessible_document_ids={
                    str(document_id)
                    for document_id in ready_ids
                },
            )

            metrics = compute_metrics(
                case, result.answer, result.sources
            )

            return self.run_repo.update(
                db,
                db_obj=run,
                status=RUN_COMPLETED,
                answer=result.answer,
                actual_sources=result.sources,
                metrics=metrics,
                completed_at=datetime.now(timezone.utc),
            )

        except (ValueError, GenerationError) as exc:
            # Application-level failures carry safe,
            # client-facing messages.
            error_detail = str(exc)
            logger.warning(
                "Evaluation run %s failed: %s",
                run.id,
                error_detail,
            )
            return self.run_repo.update(
                db,
                db_obj=run,
                status=RUN_FAILED,
                error=error_detail,
                completed_at=datetime.now(timezone.utc),
            )

        except Exception as exc:
            logger.error(
                "Evaluation run %s failed: %s",
                run.id,
                type(exc).__name__,
            )
            return self.run_repo.update(
                db,
                db_obj=run,
                status=RUN_FAILED,
                error=(
                    "Evaluation run failed: "
                    f"{type(exc).__name__}"
                ),
                completed_at=datetime.now(timezone.utc),
            )

    def _ready_document_ids(
        self, db: Session, workspace_id: int
    ) -> list[int]:
        return [
            document.id
            for document in db.query(Document.id)
            .filter(
                Document.workspace_id == workspace_id,
                Document.indexing_status == "completed",
            )
            .all()
        ]

    def _verify_selected_documents(
        self,
        db: Session,
        workspace_id: int,
        document_ids: list[int],
    ) -> list[int]:
        """Verify ownership and readiness of the
        documents selected for the test case."""
        unique_ids = set(document_ids)

        documents = (
            db.query(Document)
            .filter(
                Document.workspace_id == workspace_id,
                Document.id.in_(unique_ids),
            )
            .all()
        )

        if len(documents) != len(unique_ids):
            raise ValueError(
                "Selected document is missing or inaccessible."
            )

        for document in documents:
            if document.indexing_status != "completed":
                raise ValueError(
                    "Selected document is not ready."
                )

        return [document.id for document in documents]
