from __future__ import annotations

from threading import RLock
from uuid import UUID, uuid4

from app.assessment.evaluator import Evaluator
from app.assessment.graph import LangGraphAssessmentController
from app.assessment.models import (
    AdaptiveAction,
    AdaptiveDecision,
    AssessmentResult,
    AssessmentSession,
    AssessmentStateResponse,
    AssessmentStatus,
    EvaluationRecord,
    Question,
    StartAssessmentResponse,
    SubmissionReason,
    SubmitResponseResponse,
)
from app.assessment.questioning import QuestionPlanner, concise_prompt
from app.assessment.scoring import build_dimension_progress, build_result
from app.repositories.base import AssessmentRepository


class AssessmentNotFoundError(LookupError):
    pass


class AssessmentCompletedError(RuntimeError):
    pass


class QuestionMismatchError(ValueError):
    pass


class DuplicateResponseError(RuntimeError):
    pass


class AssessmentService:
    def __init__(
        self,
        repository: AssessmentRepository,
        evaluator: Evaluator,
        planner: QuestionPlanner | None = None,
        max_questions: int = 7,
    ) -> None:
        self.repository = repository
        self.evaluator = evaluator
        self.planner = planner or QuestionPlanner()
        self.controller = LangGraphAssessmentController(evaluator, self.planner)
        self.max_questions = max_questions
        self._submission_lock = RLock()

    def start(self, candidate) -> StartAssessmentResponse:
        session = AssessmentSession(
            id=uuid4(),
            candidate=candidate,
            max_questions=self.max_questions,
        )
        question = self.controller.initialize(session)
        session.questions.append(question)
        session.current_question = question
        self.repository.create(session)
        return StartAssessmentResponse(
            assessment_id=session.id,
            status=session.status,
            progress=session.progress,
            question=question,
            max_questions=session.max_questions,
        )

    def submit(
        self,
        assessment_id: UUID,
        question_id: UUID,
        content: str,
        submission_reason: SubmissionReason = SubmissionReason.MANUAL,
        time_spent_seconds: int | None = None,
    ) -> SubmitResponseResponse:
        with self._submission_lock:
            return self._submit_locked(
                assessment_id,
                question_id,
                content,
                submission_reason,
                time_spent_seconds,
            )

    def _submit_locked(
        self,
        assessment_id: UUID,
        question_id: UUID,
        content: str,
        submission_reason: SubmissionReason,
        time_spent_seconds: int | None,
    ) -> SubmitResponseResponse:
        session = self._get_or_raise(assessment_id)
        existing = next(
            (record for record in session.records if record.question.id == question_id), None
        )
        if existing and _normalize_answer(existing.response_text) == _normalize_answer(content):
            return SubmitResponseResponse(
                assessment_id=session.id,
                status=session.status,
                progress=session.progress,
                evaluation=existing.evaluation,
                adaptive_decision=AdaptiveDecision(
                    action=AdaptiveAction.REPLAY,
                    reason=(
                        "The same answer was already accepted; the existing state was replayed "
                        "without evaluating or writing it twice."
                    ),
                    evidence_sufficient=True,
                ),
                question=_display_question(session.current_question),
                result=session.result,
                replayed=True,
            )
        if existing:
            raise DuplicateResponseError("This question has already been answered")
        if session.status == AssessmentStatus.COMPLETED:
            raise AssessmentCompletedError("Assessment is already completed")
        if session.current_question is None or session.current_question.id != question_id:
            raise QuestionMismatchError("Response does not match the active question")

        evaluation = self.evaluator.evaluate(session.candidate, session.current_question, content)
        record = EvaluationRecord(
            question=session.current_question,
            response_text=content,
            evaluation=evaluation,
            submission_reason=submission_reason,
            time_spent_seconds=time_spent_seconds,
        )
        session.records.append(record)

        next_question, adaptive_decision = self.controller.advance(session, evaluation)
        self.repository.add_response(assessment_id, record)
        if next_question:
            session.questions.append(next_question)
            session.current_question = next_question
            self.repository.add_question(assessment_id, next_question)
        else:
            session.current_question = None
            session.status = AssessmentStatus.COMPLETED
            session.result = build_result(session, self.evaluator.model_name)

        self.repository.update(session)
        return SubmitResponseResponse(
            assessment_id=session.id,
            status=session.status,
            progress=session.progress,
            evaluation=evaluation,
            adaptive_decision=adaptive_decision,
            question=_display_question(next_question),
            result=session.result,
        )

    def get_state(self, assessment_id: UUID) -> AssessmentStateResponse:
        session = self._get_or_raise(assessment_id)
        return AssessmentStateResponse(
            assessment_id=session.id,
            status=session.status,
            progress=session.progress,
            candidate=session.candidate,
            question=_display_question(session.current_question),
            questions_answered=len(session.records),
            max_questions=session.max_questions,
            dimension_progress=build_dimension_progress(session),
            memory=session.memory,
            result=session.result,
        )

    def get_result(self, assessment_id: UUID) -> AssessmentResult:
        session = self._get_or_raise(assessment_id)
        if session.status != AssessmentStatus.COMPLETED or not session.result:
            raise AssessmentCompletedError("Assessment is not complete yet")
        return session.result

    def _get_or_raise(self, assessment_id: UUID) -> AssessmentSession:
        session = self.repository.get(assessment_id)
        if not session:
            raise AssessmentNotFoundError(f"Assessment {assessment_id} was not found")
        return session


def _normalize_answer(value: str) -> str:
    return " ".join(value.split())


def _display_question(question: Question | None) -> Question | None:
    if question is None:
        return None
    prompt = concise_prompt(question.prompt)
    return question if prompt == question.prompt else question.model_copy(update={"prompt": prompt})
