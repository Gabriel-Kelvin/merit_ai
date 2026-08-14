from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.assessment.evaluator import DeterministicEvaluator, GeminiEvaluator
from app.assessment.service import AssessmentService
from app.config import Settings, get_settings
from app.repositories.memory import MemoryAssessmentRepository
from app.repositories.supabase import SupabaseAssessmentRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_service(settings: Settings) -> AssessmentService:
    if settings.merit_storage_mode == "supabase":
        repository = SupabaseAssessmentRepository(
            settings.supabase_url, settings.supabase_secret_key
        )
    else:
        repository = MemoryAssessmentRepository()

    evaluator = (
        GeminiEvaluator(settings.gemini_api_key, settings.gemini_model)
        if settings.gemini_api_key
        else DeterministicEvaluator()
    )
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
            "Adaptive, evidence-backed engineering readiness assessment. AI evaluates evidence; "
            "application code controls workflow, scoring, persistence, and recommendations."
        ),
    )
    app.state.assessment_service = service or build_service(settings)
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
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

    @app.get("/health", tags=["system"])
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
