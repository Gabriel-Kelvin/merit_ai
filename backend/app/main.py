from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.assessment.evaluator import (
    DeterministicEvaluator,
    FallbackEvaluator,
    GeminiEvaluator,
    OpenRouterEvaluator,
)
from app.assessment.service import AssessmentService
from app.config import Settings, get_settings
from app.repositories.memory import MemoryAssessmentRepository
from app.repositories.supabase import SupabaseAssessmentRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {
        "name": "assessment",
        "description": (
            "Start, answer, resume, and inspect adaptive evidence-backed assessments. The AI "
            "evaluates answers; deterministic application rules control flow and scoring."
        ),
    },
    {
        "name": "system",
        "description": "Operational health and active backend configuration.",
    },
]


def build_service(settings: Settings) -> AssessmentService:
    if settings.merit_storage_mode == "supabase":
        repository = SupabaseAssessmentRepository(
            settings.supabase_url, settings.supabase_secret_key
        )
    else:
        repository = MemoryAssessmentRepository()

    primary = (
        GeminiEvaluator(settings.gemini_api_key, settings.gemini_model)
        if settings.gemini_api_key
        else None
    )
    fallback = (
        OpenRouterEvaluator(settings.openrouter_api_key, settings.openrouter_model)
        if settings.openrouter_api_key
        else None
    )
    if primary and fallback:
        evaluator = FallbackEvaluator(primary, fallback)
    else:
        evaluator = primary or fallback or DeterministicEvaluator()
    return AssessmentService(
        repository=repository,
        evaluator=evaluator,
        max_questions=settings.merit_max_questions,
    )


def create_app(
    service: AssessmentService | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Merit AI Assessment API",
        version=settings.app_version,
        description=(
            "## An explainable adaptive engineering assessment\n\n"
            "Merit AI asks questions grounded in a candidate's own projects and changes its next "
            "move after every answer. Each response produces rubric-signal verdicts, evidence, a "
            "calibrated score, and confidence.\n\n"
            "### Trust boundaries\n"
            "- Gemini performs constrained, structured evidence evaluation.\n"
            "- Application code controls dimension coverage, follow-ups, stopping, weighting, and "
            "classification.\n"
            "- Supabase stores every accepted question, answer, evaluation, and final audit "
            "trace.\n"
            "- Repeated identical submissions are replayed safely instead of evaluated twice.\n\n"
            "The practical IDE challenge, payment, GitHub integration, and deployment concerns are "
            "intentionally outside this API's current scope."
        ),
        openapi_tags=OPENAPI_TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        swagger_ui_parameters={
            "displayRequestDuration": True,
            "filter": True,
            "operationsSorter": "method",
            "tagsSorter": "alpha",
            "tryItOutEnabled": True,
        },
    )
    app.state.assessment_service = service or build_service(settings)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(
            dict.fromkeys(
                [
                    settings.frontend_origin,
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                ]
            )
        ),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid4()))
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request error", extra={"request_id": request_id})
            response = JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "The request could not be completed.",
                        "request_id": request_id,
                    }
                },
            )
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get(
        "/health",
        tags=["system"],
        summary="Check API health",
        description="Confirms the process is healthy and identifies active storage and AI modes.",
        operation_id="getHealth",
    )
    def health() -> dict:
        return {
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
            "storage": settings.merit_storage_mode,
            "ai_model": app.state.assessment_service.evaluator.model_name,
        }

    app.include_router(router, tags=["assessment"])
    return app


app = create_app()
