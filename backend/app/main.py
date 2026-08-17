from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.accounts import MemoryAccountService, SupabaseAccountService
from app.api.auth_routes import router as auth_router
from app.api.profile_routes import router as profile_router
from app.api.resume_routes import router as resume_router
from app.api.routes import router
from app.assessment.evaluator import (
    FallbackEvaluator,
    GeminiEvaluator,
    GroqEvaluator,
    OfflineEvidenceEvaluator,
    OpenRouterEvaluator,
)
from app.assessment.service import AssessmentService
from app.config import Settings, get_settings
from app.profiles import MemoryCandidateProfileStore, SupabaseCandidateProfileStore
from app.repositories.memory import MemoryAssessmentRepository
from app.repositories.supabase import SupabaseAssessmentRepository
from app.resumes.parser import ResumeParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAPI_TAGS = [
    {
        "name": "authentication",
        "description": "Candidate signup, login, current session, and logout endpoints.",
    },
    {
        "name": "profile",
        "description": "Account-level candidate profile and parsed resume-context persistence.",
    },
    {
        "name": "assessment",
        "description": (
            "Start, answer, resume, and inspect adaptive evidence-backed assessments. The AI "
            "generates role-specific capabilities and questions, then evaluates answers. "
            "Application rules validate outputs and control safe scoring and stopping."
        ),
    },
    {
        "name": "system",
        "description": "Operational health and active backend configuration.",
    },
    {
        "name": "resume",
        "description": "In-memory resume parsing for selective candidate-profile autofill.",
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
    groq = (
        GroqEvaluator(settings.groq_api_key, settings.groq_model)
        if settings.groq_api_key
        else None
    )
    openrouter = (
        OpenRouterEvaluator(settings.openrouter_api_key, settings.openrouter_model)
        if settings.openrouter_api_key
        else None
    )
    providers = [provider for provider in (primary, groq, openrouter) if provider]
    evaluator = OfflineEvidenceEvaluator()
    for provider in reversed(providers):
        if isinstance(provider, GeminiEvaluator):
            primary_timeout, fallback_timeout = 10, 12
        elif isinstance(provider, GroqEvaluator):
            primary_timeout, fallback_timeout = 4, 7
        else:
            primary_timeout, fallback_timeout = 5, 1
        evaluator = FallbackEvaluator(
            provider,
            evaluator,
            primary_timeout=primary_timeout,
            fallback_timeout=fallback_timeout,
            cooldown_seconds=8,
        )
    return AssessmentService(
        repository=repository,
        evaluator=evaluator,
        max_questions=settings.merit_max_questions,
    )


def build_account_service(settings: Settings):
    if settings.merit_storage_mode == "supabase":
        return SupabaseAccountService(
            settings.supabase_url,
            settings.supabase_publishable_key,
            settings.supabase_secret_key,
        )
    return MemoryAccountService()


def create_app(
    service: AssessmentService | None = None, settings: Settings | None = None
) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Merit AI Assessment API",
        version=settings.app_version,
        description=(
            "## An explainable adaptive engineering assessment\n\n"
            "Merit AI uses a checkpointed LangGraph state machine to generate a role-specific "
            "capability map, remember the conversation, and change its next move after every "
            "answer. Each response "
            "produces capability-signal verdicts, evidence, a "
            "calibrated score, and confidence.\n\n"
            "### Trust boundaries\n"
            "- Gemini performs constrained blueprint, question, and evidence generation, with "
            "Groq and OpenRouter as bounded fallbacks.\n"
            "- LangGraph controls memory updates, topic switching, coverage, and transitions.\n"
            "- Application code validates generated capabilities and controls coverage, "
            "follow-ups, stopping, calibrated scoring, and classification.\n"
            "- Supabase stores every accepted question, answer, evaluation, and final audit "
            "trace.\n"
            "- Repeated identical submissions are replayed safely instead of evaluated twice.\n\n"
            "The practical IDE challenge and payment integration are intentionally outside this "
            "API's current scope."
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
    app.state.profile_store = (
        SupabaseCandidateProfileStore(settings.supabase_url, settings.supabase_secret_key)
        if settings.merit_storage_mode == "supabase"
        else MemoryCandidateProfileStore()
    )
    app.state.resume_parser = (
        ResumeParser(
            settings.gemini_api_key,
            settings.gemini_model,
            settings.openrouter_api_key,
            settings.openrouter_model,
        )
        if settings.gemini_api_key or settings.openrouter_api_key
        else None
    )
    app.state.settings = settings
    app.state.account_service = build_account_service(settings)
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
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
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
        "/",
        tags=["system"],
        summary="Merit AI API landing response",
        operation_id="getApiLanding",
    )
    def api_landing() -> dict:
        return {
            "message": "Merit AI Assessment API is running.",
            "frontend": settings.frontend_origin,
            "swagger_docs": "/docs",
            "redoc": "/redoc",
            "health": "/health",
            "resume_parser": "/api/v1/resumes/parse",
        }

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
            "ai_providers": {
                "gemini": bool(settings.gemini_api_key),
                "groq": bool(settings.groq_api_key),
                "openrouter": bool(settings.openrouter_api_key),
            },
            "orchestration": "langgraph-v1",
            "max_questions": settings.merit_max_questions,
        }

    app.include_router(auth_router)
    app.include_router(profile_router)
    app.include_router(router, tags=["assessment"])
    app.include_router(resume_router)
    return app


app = create_app()
