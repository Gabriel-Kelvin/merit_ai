from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.assessment.models import (
    AssessmentResult,
    AssessmentStateResponse,
    StartAssessmentRequest,
    StartAssessmentResponse,
    SubmitResponseRequest,
    SubmitResponseResponse,
)
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


@router.post(
    "/assessments",
    response_model=StartAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start an adaptive readiness assessment",
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
    except (AssessmentCompletedError, QuestionMismatchError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentStateResponse,
    summary="Resume or inspect an assessment",
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
