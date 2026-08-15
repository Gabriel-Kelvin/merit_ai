from uuid import uuid4

import pytest

from app.assessment.evaluator import DeterministicEvaluator, EvaluationUnavailableError
from app.assessment.models import CandidateContext, ProjectExperience
from app.assessment.service import (
    AssessmentService,
    DuplicateResponseError,
)
from app.repositories.memory import MemoryAssessmentRepository


@pytest.fixture
def candidate() -> CandidateContext:
    return CandidateContext(
        name="Arjun Rao",
        email="arjun@example.com",
        education="B.Tech Computer Science",
        graduation_year=2026,
        experience_level="fresher",
        target_role="AI Engineer",
        technical_skills=["Python", "FastAPI", "React", "PostgreSQL"],
        projects=[
            ProjectExperience(
                name="Campus support assistant",
                description="A React and FastAPI application that routes student questions.",
                technologies=["React", "FastAPI", "PostgreSQL"],
            )
        ],
        ai_tools_used=["Gemini", "Codex"],
    )


@pytest.fixture
def service() -> AssessmentService:
    return AssessmentService(
        MemoryAssessmentRepository(), DeterministicEvaluator(), max_questions=20
    )


def test_personalized_first_question(service, candidate):
    started = service.start(candidate)
    assert started.question.prompt.startswith("Tell me about yourself")
    assert started.question.assessment_area == "introduction"
    assert started.question.time_limit_seconds in {120, 180, 300}
    assert started.question.expires_at is not None
    assert started.progress == 0


def test_start_recovers_with_role_specific_blueprint_when_providers_are_busy(candidate):
    class PlanningUnavailable(DeterministicEvaluator):
        def plan_assessment(self, candidate):
            del candidate
            raise EvaluationUnavailableError(30)

    recovering_service = AssessmentService(
        MemoryAssessmentRepository(), PlanningUnavailable(), max_questions=20
    )

    started = recovering_service.start(candidate)
    state = recovering_service.get_state(started.assessment_id)

    assert started.question.prompt.startswith("Tell me about yourself")
    assert state.dimension_progress
    assert all("AI Engineer" in item.label for item in state.dimension_progress[:1])


def test_mechanical_role_receives_domain_specific_capabilities(service):
    candidate = CandidateContext(
        name="Ananya Rao",
        education="B.E. Mechanical Engineering",
        experience_level="fresher",
        target_role="Mechanical Design Engineer",
        technical_skills=["SolidWorks", "ANSYS", "GD&T"],
    )

    started = service.start(candidate)
    state = service.get_state(started.assessment_id)
    labels = [item.label.lower() for item in state.dimension_progress]

    assert started.question.prompt.startswith("Tell me about yourself")
    assert not any("agentic" in label or "ai fluency" in label for label in labels)


def test_topic_switch_updates_langgraph_memory_and_redirects(service, candidate):
    started = service.start(candidate)
    redirected = service.submit(
        started.assessment_id,
        started.question.id,
        "I don't know. Please ask me something else on an unrelated topic.",
    )

    state = service.repository.get(started.assessment_id)
    assert redirected.adaptive_decision.action == "change_topic"
    assert redirected.question is not None
    assert redirected.question.assessment_area != started.question.assessment_area
    assert state is not None
    assert state.memory.graph_version == "langgraph-v1"
    assert state.memory.avoided_topics
    assert state.memory.conversation_summary


def test_expired_blank_answer_is_recorded_and_advances(service, candidate):
    started = service.start(candidate)
    submitted = service.submit(
        started.assessment_id,
        started.question.id,
        "",
        submission_reason="time_expired",
        time_spent_seconds=180,
    )

    state = service.repository.get(started.assessment_id)
    assert submitted.question is not None
    assert state is not None
    assert state.records[0].response_text == ""
    assert state.records[0].submission_reason == "time_expired"
    assert state.records[0].time_spent_seconds == 180


def test_weak_answer_triggers_focused_follow_up(service, candidate):
    started = service.start(candidate)
    after_intro = service.submit(
        started.assessment_id,
        started.question.id,
        "I would send it to the backend and save it.",
    )
    submitted = service.submit(
        started.assessment_id,
        after_intro.question.id,
        "I would send it to the backend and save it.",
    )
    assert submitted.question is not None
    assert submitted.question.dimension == after_intro.question.dimension
    assert submitted.evaluation.follow_up_required is True
    assert submitted.adaptive_decision.action == "probe_gap"
    assert submitted.question.is_follow_up is True
    assert submitted.question.parent_question_id == after_intro.question.id


def test_strong_answer_advances_to_next_role_specific_capability(service, candidate):
    started = service.start(candidate)
    submitted = service.submit(
        started.assessment_id,
        started.question.id,
        (
            "I apply the correct principles to a concrete applied example, document constraints, "
            "compare trade-offs, and verify the result against objective acceptance criteria. "
            "I record the evidence, review failure cases, and communicate the decision clearly."
        ),
    )
    assert submitted.adaptive_decision.action == "advance"
    assert submitted.question is not None
    assert submitted.question.assessment_area == "experience"
    assert submitted.question.dimension != started.question.dimension


def test_duplicate_submission_is_rejected(service, candidate):
    started = service.start(candidate)
    service.submit(
        started.assessment_id,
        started.question.id,
        "I would send it to the backend and save it.",
    )
    with pytest.raises(DuplicateResponseError):
        service.submit(
            started.assessment_id,
            started.question.id,
            "Submitting the same answer again must fail.",
        )


def test_identical_submission_is_idempotently_replayed(service, candidate):
    started = service.start(candidate)
    content = "I would send it to the backend, validate it, and save it."
    original = service.submit(started.assessment_id, started.question.id, content)
    replay = service.submit(
        started.assessment_id,
        started.question.id,
        "  I would send it to the backend, validate it, and save it.  ",
    )
    assert replay.replayed is True
    assert replay.adaptive_decision.action == "replay"
    assert replay.evaluation == original.evaluation


def test_wrong_question_is_rejected(service, candidate):
    started = service.start(candidate)
    with pytest.raises(ValueError):
        service.submit(started.assessment_id, uuid4(), "A valid but mismatched answer")


def test_question_generation_failure_does_not_persist_the_answer(candidate):
    class FailsAfterEvaluation(DeterministicEvaluator):
        def generate_question(
            self, candidate, blueprint, dimension, history, action, focus
        ):
            if history:
                raise EvaluationUnavailableError(20)
            return super().generate_question(
                candidate, blueprint, dimension, history, action, focus
            )

    service = AssessmentService(
        MemoryAssessmentRepository(), FailsAfterEvaluation(), max_questions=7
    )
    started = service.start(candidate)

    with pytest.raises(EvaluationUnavailableError):
        service.submit(
            started.assessment_id,
            started.question.id,
            "A response with enough content to require a next adaptive question.",
        )

    assert service.get_state(started.assessment_id).questions_answered == 0


def test_complete_assessment_returns_evidence_backed_result(service, candidate):
    state = service.start(candidate)
    final = None
    while state.question is not None:
        final = service.submit(
            state.assessment_id,
            state.question.id,
            (
                "I start with data flow and validation, reproduce the failure, inspect logs and "
                "evidence, rank hypotheses, apply a safe fix, and verification includes tests. "
                "For AI I define appropriate delegation, limitations, security constraints, scope, "
                "an incremental plan, acceptance criteria, plain language, risk and recommendation."
            ),
        )
        if final.question is None:
            break
        state = final

    assert final is not None
    assert final.status == "completed"
    assert final.progress == 100
    assert final.result is not None
    assert len(final.result.dimensions) == 3
    assert final.result.readiness_score > 0
    assert final.result.recommendation.proof_of_improvement_challenge is None
    assert final.result.evaluation_trace
    assert final.result.overall_confidence > 0
    assert all(item.rationale for item in final.result.dimensions)
