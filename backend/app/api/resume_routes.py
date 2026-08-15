from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.assessment.models import ErrorResponse
from app.auth import require_demo_user
from app.resumes.models import ResumeParseResponse
from app.resumes.parser import (
    MAX_RESUME_BYTES,
    ResumeFormatError,
    ResumeParser,
    ResumeParsingUnavailableError,
)

router = APIRouter(
    prefix="/api/v1/resumes",
    tags=["resume"],
    dependencies=[Depends(require_demo_user)],
)


def get_parser(request: Request) -> ResumeParser:
    parser = request.app.state.resume_parser
    if parser is None:
        raise HTTPException(status_code=503, detail="Resume extraction is not configured")
    return parser


@router.post(
    "/parse",
    response_model=ResumeParseResponse,
    summary="Extract candidate profile fields from a resume",
    description=(
        "Accepts PDF, DOCX, or TXT up to 5 MB. Only fields supported by readable resume text are "
        "returned; uncertain fields remain null or empty so the candidate can complete them. The "
        "raw file is processed in memory and is not stored by this endpoint."
    ),
    operation_id="parseResume",
    responses={
        400: {"model": ErrorResponse, "description": "Resume is unreadable or unsupported."},
        413: {"model": ErrorResponse, "description": "Resume exceeds 5 MB."},
        503: {"model": ErrorResponse, "description": "AI extraction is temporarily unavailable."},
    },
)
async def parse_resume(
    request: Request,
    file: Annotated[UploadFile, File(description="PDF, DOCX, or TXT resume")],
) -> ResumeParseResponse:
    content = await file.read(MAX_RESUME_BYTES + 1)
    if len(content) > MAX_RESUME_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Resume must be 5 MB or smaller",
        )
    try:
        return await run_in_threadpool(
            get_parser(request).parse,
            file.filename or "",
            content,
        )
    except ResumeFormatError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ResumeParsingUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
