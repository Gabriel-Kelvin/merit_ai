from uuid import uuid4

import pytest

from app.assessment.evaluator import DeterministicEvaluator
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
        MemoryAssessmentRepository(), DeterministicEvaluator(), max_questions=7
    )


def test_personalized_first_question(service, candidate):
    started = service.start(candidate)
    assert "Campus support assistant" in started.question.prompt
    assert started.progress == 0


def test_weak_answer_triggers_focused_follow_up(service, candidate):
    started = service.start(candidate)
    submitted = service.submit(
        started.assessment_id,
        started.question.id,
        "I would send it to the backend and save it.",
    )
    assert submitted.question is not None
    assert submitted.question.dimension == started.question.dimension
    assert submitted.evaluation.follow_up_required is True
    assert submitted.adaptive_decision.action == "probe_gap"
    assert submitted.question.is_follow_up is True
    assert submitted.question.parent_question_id == started.question.id


def test_strong_answer_increases_difficulty(service, candidate):
    started = service.start(candidate)
    submitted = service.submit(
        started.assessment_id,
        started.question.id,
        (
            "I map the data flow from React through FastAPI to PostgreSQL. I use schema validation "
            "at the boundary, explicit failure handling with safe user errors and structured logs, "
            "and verification through integration tests, database constraints, and observed traces "
            "before release. I also document transaction ownership and rollback behavior."
        ),
    )
    assert submitted.adaptive_decision.action == "stretch"
    assert submitted.question is not None
    assert submitted.question.difficulty == "advanced"
    assert "identical requests" in submitted.question.prompt


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
    assert len(final.result.dimensions) == 5
    assert final.result.readiness_score > 0
    assert final.result.recommendation.proof_of_improvement_challenge is None
    assert final.result.evaluation_trace
    assert final.result.overall_confidence > 0
    assert all(item.rationale for item in final.result.dimensions)
