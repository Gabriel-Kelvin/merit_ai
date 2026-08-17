from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.assessment.evaluator import EvaluationUnavailableError
from app.assessment.models import (
    AssessmentMethodologyResponse,
    AssessmentResult,
    AssessmentStateResponse,
    ErrorResponse,
    StartAssessmentRequest,
    StartAssessmentResponse,
    SubmitResponseRequest,
    SubmitResponseResponse,
)
from app.assessment.service import (
    AssessmentCompletedError,
    AssessmentForbiddenError,
    AssessmentNotFoundError,
    AssessmentService,
    DuplicateResponseError,
    QuestionMismatchError,
)
from app.auth import require_user

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_user)])


def get_service(request: Request) -> AssessmentService:
    return request.app.state.assessment_service


ServiceDependency = Annotated[AssessmentService, Depends(get_service)]
AccountDependency = Annotated[str, Depends(require_user)]


@router.get(
    "/assessment-methodology",
    response_model=AssessmentMethodologyResponse,
    summary="Inspect the assessment methodology",
    description=(
        "Returns the public evidence principles and adaptive stopping rules. Role-specific "
        "capabilities and weights are generated when each assessment starts. "
        "This endpoint makes the engine's evaluation contract inspectable without exposing model "
        "chain-of-thought or private credentials."
    ),
    operation_id="getAssessmentMethodology",
)
def get_methodology() -> AssessmentMethodologyResponse:
    return AssessmentMethodologyResponse(
        principles=[
            "Score only evidence present in the candidate's answer.",
            "Do not reward verbosity, buzzwords, claimed seniority, or self-awarded scores.",
            "Ground every conclusion in a recorded evidence item and rubric signal.",
            "Generate capabilities from the candidate's role, resume, and professional context.",
            "Generate every next question from accumulated answers, evidence, and uncertainty.",
            "Use LangGraph state to track coverage, topic changes, skipped areas, and memory.",
            "Keep AI content generation separate from score calibration and safety controls.",
        ],
        stopping_rules=[
            "Weak, unclear, or low-confidence evidence may trigger a focused probe when capacity "
            "remains.",
            "A request to skip or change topic redirects immediately and is retained in state.",
            "Strong evidence may trigger a higher-difficulty role-specific stretch question.",
            "Sufficient evidence advances to the next generated capability.",
            "Every capability in the candidate-specific blueprint receives coverage before "
            "optional probes consume remaining slots.",
            "The assessment stops early when coverage is sufficient or at the hard maximum of "
            "20 questions.",
            "Every question receives an AI-selected 2, 3, or 5 minute window.",
        ],
        dimensions=[],
    )


@router.post(
    "/assessments",
    response_model=StartAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an adaptive readiness assessment",
    description=(
        "Creates a durable assessment session and returns a question personalized from the "
        "candidate's resume, target role, experience, and projects. The AI first generates a "
        "role-specific capability blueprint, while the opening question is always 'Tell me about "
        "yourself' so the candidate's own narrative precedes resume-based probing."
    ),
    operation_id="startAssessment",
    responses={
        422: {"model": ErrorResponse, "description": "Candidate context is invalid."},
        503: {"model": ErrorResponse, "description": "Dynamic assessment planning unavailable."},
    },
)
def start_assessment(
    payload: StartAssessmentRequest,
    service: ServiceDependency,
    account_id: AccountDependency,
) -> StartAssessmentResponse:
    try:
        return service.start(payload.candidate, account_id=account_id)
    except EvaluationUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="Dynamic assessment planning is temporarily unavailable.",
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc


@router.post(
    "/assessments/{assessment_id}/responses",
    response_model=SubmitResponseResponse,
    summary="Evaluate a response and return the next adaptive state",
    description=(
        "Evaluates the active answer against explicit signals, persists its evidence, and returns "
        "the LangGraph engine's visible adaptive decision: probe a gap, change topic, increase "
        "difficulty, advance, or complete. Timer-expired partial and empty answers are accepted. "
        "Repeating the same question ID and normalized answer is idempotent and replays "
        "the accepted state without a second AI call or database write."
    ),
    operation_id="submitAssessmentResponse",
    responses={
        400: {"model": ErrorResponse, "description": "Question is not the active question."},
        404: {"model": ErrorResponse, "description": "Assessment was not found."},
        409: {"model": ErrorResponse, "description": "Question already has a different answer."},
        422: {"model": ErrorResponse, "description": "Answer payload is invalid."},
        503: {
            "model": ErrorResponse,
            "description": "AI evaluator quota or provider capacity is temporarily unavailable.",
        },
    },
)
def submit_response(
    assessment_id: UUID,
    payload: SubmitResponseRequest,
    service: ServiceDependency,
    account_id: AccountDependency,
) -> SubmitResponseResponse:
    try:
        return service.submit(
            assessment_id,
            payload.question_id,
            payload.content,
            payload.submission_reason,
            payload.time_spent_seconds,
            account_id=account_id,
        )
    except (AssessmentNotFoundError, AssessmentForbiddenError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DuplicateResponseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except EvaluationUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
    except (AssessmentCompletedError, QuestionMismatchError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentStateResponse,
    summary="Resume or inspect an assessment",
    description=(
        "Returns the exact persisted question plus evidence sufficiency and confidence for every "
        "dimension. Clients can use this endpoint after a refresh to resume safely."
    ),
    operation_id="getAssessmentState",
    responses={404: {"model": ErrorResponse, "description": "Assessment was not found."}},
)
def get_assessment(
    assessment_id: UUID,
    service: ServiceDependency,
    account_id: AccountDependency,
) -> AssessmentStateResponse:
    try:
        return service.get_state(assessment_id, account_id=account_id)
    except (AssessmentNotFoundError, AssessmentForbiddenError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/assessments/{assessment_id}/result",
    response_model=AssessmentResult,
    summary="Get the final evidence-backed readiness result",
    description=(
        "Returns the weighted readiness map, confidence, evidence ledger, per-question evaluation "
        "trace, limiting gaps, and a specific development plan. A result is never available before "
        "the assessment has completed."
    ),
    operation_id="getAssessmentResult",
    responses={
        404: {"model": ErrorResponse, "description": "Assessment was not found."},
        409: {"model": ErrorResponse, "description": "Assessment is still in progress."},
    },
)
def get_result(
    assessment_id: UUID,
    service: ServiceDependency,
    account_id: AccountDependency,
) -> AssessmentResult:
    try:
        return service.get_result(assessment_id, account_id=account_id)
    except (AssessmentNotFoundError, AssessmentForbiddenError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AssessmentCompletedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
