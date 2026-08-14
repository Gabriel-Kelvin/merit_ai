from __future__ import annotations

from uuid import UUID, uuid4

from app.assessment.evaluator import Evaluator
from app.assessment.models import (
    AssessmentResult,
    AssessmentSession,
    AssessmentStateResponse,
    AssessmentStatus,
    EvaluationRecord,
    StartAssessmentResponse,
    SubmitResponseResponse,
)
from app.assessment.questioning import QuestionPlanner
from app.assessment.scoring import build_result
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
        self.max_questions = max_questions

    def start(self, candidate) -> StartAssessmentResponse:
        session = AssessmentSession(
            id=uuid4(),
            candidate=candidate,
            max_questions=self.max_questions,
        )
        question = self.planner.first_question(session)
        session.questions.append(question)
        session.current_question = question
        self.repository.create(session)
        return StartAssessmentResponse(
            assessment_id=session.id,
            status=session.status,
            progress=session.progress,
            question=question,
        )

    def submit(
        self, assessment_id: UUID, question_id: UUID, content: str
    ) -> SubmitResponseResponse:
        session = self._get_or_raise(assessment_id)
        if session.status == AssessmentStatus.COMPLETED:
            raise AssessmentCompletedError("Assessment is already completed")
        if any(record.question.id == question_id for record in session.records):
            raise DuplicateResponseError("This question has already been answered")
        if session.current_question is None or session.current_question.id != question_id:
            raise QuestionMismatchError("Response does not match the active question")

        evaluation = self.evaluator.evaluate(session.candidate, session.current_question, content)
        record = EvaluationRecord(
            question=session.current_question,
            response_text=content,
            evaluation=evaluation,
        )
        self.repository.add_response(assessment_id, record)
        session.records.append(record)

        next_question = self.planner.next_question(session, evaluation)
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
            question=next_question,
            result=session.result,
        )

    def get_state(self, assessment_id: UUID) -> AssessmentStateResponse:
        session = self._get_or_raise(assessment_id)
        return AssessmentStateResponse(
            assessment_id=session.id,
            status=session.status,
            progress=session.progress,
            candidate=session.candidate,
            question=session.current_question,
            questions_answered=len(session.records),
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
