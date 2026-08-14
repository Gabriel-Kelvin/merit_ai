from uuid import uuid4

import pytest

from app.assessment.evaluator import (
    EvaluationUnavailableError,
    FallbackEvaluator,
    GeminiEvaluator,
    OpenRouterEvaluator,
    _retry_after_seconds,
)
from app.assessment.models import (
    CandidateContext,
    Difficulty,
    Dimension,
    Question,
    QuestionType,
    ResponseEvaluation,
    SignalAssessment,
    SignalStatus,
)


def engineering_question() -> Question:
    return Question(
        id=uuid4(),
        sequence_no=1,
        dimension=Dimension.ENGINEERING_FUNDAMENTALS,
        type=QuestionType.TEXT,
        difficulty=Difficulty.STANDARD,
        prompt="Explain the request flow.",
        intent="Collect engineering evidence.",
        expected_signals=["data flow", "validation", "failure handling", "verification"],
    )


def test_missing_signals_cap_an_overconfident_model_score():
    evaluation = ResponseEvaluation(
        score=96,
        confidence=0.94,
        evidence=[],
        strengths=["Mentions a frontend and backend"],
        gaps=["No failure handling", "No verification"],
        follow_up_required=False,
        signal_assessments=[
            SignalAssessment(
                signal="data flow",
                status=SignalStatus.PARTIAL,
                explanation="Only component names were supplied.",
            ),
            SignalAssessment(
                signal="validation",
                status=SignalStatus.MISSING,
                explanation="Validation was not discussed.",
            ),
            SignalAssessment(
                signal="failure handling",
                status=SignalStatus.MISSING,
                explanation="Failure behavior was not discussed.",
            ),
            SignalAssessment(
                signal="verification",
                status=SignalStatus.MISSING,
                explanation="No objective checks were supplied.",
            ),
        ],
        reasoning_summary="The answer names components but does not explain the mechanisms.",
    )

    calibrated = GeminiEvaluator._calibrate(evaluation, engineering_question())

    assert calibrated.score == 69
    assert calibrated.follow_up_required is True
    assert calibrated.follow_up_focus == "validation"


def test_off_topic_answer_receives_low_score_and_confidence_caps():
    evaluation = ResponseEvaluation(
        score=88,
        confidence=0.92,
        evidence=[],
        strengths=[],
        gaps=["The answer is off topic"],
        follow_up_required=False,
        answer_relevance=0.2,
        reasoning_summary="The answer does not address the question.",
    )

    calibrated = GeminiEvaluator._calibrate(evaluation, engineering_question())

    assert calibrated.score <= 39
    assert calibrated.confidence <= 0.55
    assert calibrated.follow_up_required is True


def test_provider_retry_delay_is_bounded_and_parseable():
    assert _retry_after_seconds("Please retry in 48.877s") == 49
    assert _retry_after_seconds("retryDelay': '7s'") == 8
    assert _retry_after_seconds("No delay supplied") == 60


def test_openrouter_fallback_rejects_non_free_models():
    with pytest.raises(ValueError, match="free"):
        OpenRouterEvaluator("test-key", "anthropic/claude-sonnet")


def test_fallback_uses_secondary_only_when_primary_is_unavailable():
    expected = ResponseEvaluation(
        score=72,
        confidence=0.8,
        evidence=[],
        strengths=["Uses explicit verification"],
        gaps=[],
        follow_up_required=False,
        reasoning_summary="The fallback returned a valid structured evaluation.",
    )

    class Primary:
        model_name = "primary-model"

        def evaluate(self, candidate, question, response_text):
            del candidate, question, response_text
            raise EvaluationUnavailableError(30)

    class FreeFallback:
        model_name = "test/free-model:free"

        def evaluate(self, candidate, question, response_text):
            del candidate, question, response_text
            return expected

    evaluator = FallbackEvaluator(Primary(), FreeFallback())
    result = evaluator.evaluate(
        CandidateContext(
            name="Fallback Test",
            experience_level="fresher",
            target_role="AI Engineer",
        ),
        engineering_question(),
        "A relevant answer.",
    )

    assert result == expected
    assert evaluator.model_name.endswith(":free")
