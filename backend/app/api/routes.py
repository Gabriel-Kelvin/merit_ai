from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.assessment.evaluator import EvaluationUnavailableError
from app.assessment.models import (
    DIMENSION_LABELS,
    AssessmentMethodologyResponse,
    AssessmentResult,
    AssessmentStateResponse,
    ErrorResponse,
    MethodologyDimension,
    StartAssessmentRequest,
    StartAssessmentResponse,
    SubmitResponseRequest,
    SubmitResponseResponse,
)
from app.assessment.rubric import DIMENSION_ORDER, RUBRICS
from app.assessment.service import (
    AssessmentCompletedError,
    AssessmentNotFoundError,
    AssessmentService,
    DuplicateResponseError,
    QuestionMismatchError,
)

router = APIRouter(prefix="/api/v1")


def get_service(request: Request) -> AssessmentService:
    return request.app.state.assessment_service


ServiceDependency = Annotated[AssessmentService, Depends(get_service)]


@router.get(
    "/assessment-methodology",
    response_model=AssessmentMethodologyResponse,
    summary="Inspect the assessment methodology",
    description=(
        "Returns the public rubric, weights, evidence principles, and adaptive stopping rules. "
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
            "Keep AI evaluation separate from deterministic workflow and final score calculation.",
        ],
        stopping_rules=[
            "Weak, unclear, or low-confidence evidence triggers one focused probe when capacity "
            "remains.",
            "Strong, high-confidence fundamentals may trigger a higher-difficulty production "
            "probe.",
            "Sufficient evidence advances to the next capability without a redundant question.",
            "All five capabilities receive coverage before optional probes consume the final "
            "slots.",
            "The assessment stops after capability coverage or the configured maximum question "
            "count.",
        ],
        dimensions=[
            MethodologyDimension(
                dimension=dimension,
                label=DIMENSION_LABELS[dimension],
                purpose=RUBRICS[dimension].purpose,
                weight=RUBRICS[dimension].weight,
                strong_signals=list(RUBRICS[dimension].strong_signals),
                weak_signals=list(RUBRICS[dimension].weak_signals),
            )
            for dimension in DIMENSION_ORDER
        ],
    )


@router.post(
    "/assessments",
    response_model=StartAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an adaptive readiness assessment",
    description=(
        "Creates a durable assessment session and returns a question personalized from the "
        "candidate's project, stack, target role, and experience. The workflow guarantees that "
        "all rubric dimensions are covered before optional follow-up probes."
    ),
    operation_id="startAssessment",
    responses={422: {"model": ErrorResponse, "description": "Candidate context is invalid."}},
)
def start_assessment(
    payload: StartAssessmentRequest,
    service: ServiceDependency,
) -> StartAssessmentResponse:
    return service.start(payload.candidate)


@router.post(
    "/assessments/{assessment_id}/responses",
    response_model=SubmitResponseResponse,
    summary="Evaluate a response and return the next adaptive state",
    description=(
        "Evaluates the active answer against explicit signals, persists its evidence, and returns "
        "the engine's visible adaptive decision: probe a gap, increase difficulty, advance, or "
        "complete. Repeating the same question ID and normalized answer is idempotent and replays "
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
) -> SubmitResponseResponse:
    try:
        return service.submit(assessment_id, payload.question_id, payload.content)
    except AssessmentNotFoundError as exc:
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
) -> AssessmentStateResponse:
    try:
        return service.get_state(assessment_id)
    except AssessmentNotFoundError as exc:
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
) -> AssessmentResult:
    try:
        return service.get_result(assessment_id)
    except AssessmentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except AssessmentCompletedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
