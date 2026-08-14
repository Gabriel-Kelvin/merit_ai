from copy import deepcopy
from threading import RLock
from uuid import UUID

from app.assessment.models import AssessmentSession, EvaluationRecord, Question


class MemoryAssessmentRepository:
    def __init__(self) -> None:
        self._sessions: dict[UUID, AssessmentSession] = {}
        self._lock = RLock()

    def create(self, session: AssessmentSession) -> None:
        with self._lock:
            self._sessions[session.id] = deepcopy(session)

    def get(self, assessment_id: UUID) -> AssessmentSession | None:
        with self._lock:
            session = self._sessions.get(assessment_id)
            return deepcopy(session) if session else None

    def add_question(self, assessment_id: UUID, question: Question) -> None:
        with self._lock:
            session = self._sessions[assessment_id]
            session.questions.append(deepcopy(question))
            session.current_question = deepcopy(question)

    def add_response(self, assessment_id: UUID, record: EvaluationRecord) -> None:
        with self._lock:
            self._sessions[assessment_id].records.append(deepcopy(record))

    def update(self, session: AssessmentSession) -> None:
        with self._lock:
            self._sessions[session.id] = deepcopy(session)
