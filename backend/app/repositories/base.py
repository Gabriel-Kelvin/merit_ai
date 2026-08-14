from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.assessment.models import AssessmentSession, EvaluationRecord, Question


class AssessmentRepository(Protocol):
    def create(self, session: AssessmentSession) -> None: ...

    def get(self, assessment_id: UUID) -> AssessmentSession | None: ...

    def add_question(self, assessment_id: UUID, question: Question) -> None: ...

    def add_response(self, assessment_id: UUID, record: EvaluationRecord) -> None: ...

    def update(self, session: AssessmentSession) -> None: ...
