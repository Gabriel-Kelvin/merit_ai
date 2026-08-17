from fastapi.testclient import TestClient

from app.assessment.evaluator import (
    DeterministicEvaluator,
    EvaluationUnavailableError,
    FallbackEvaluator,
    OfflineEvidenceEvaluator,
)
from app.assessment.questioning import concise_prompt
from app.assessment.service import AssessmentService
from app.config import Settings
from app.main import create_app
from app.repositories.memory import MemoryAssessmentRepository
from app.resumes.models import ResumeParseResponse, ResumeProfile


def make_client(evaluator=None) -> TestClient:
    service = AssessmentService(
        MemoryAssessmentRepository(), evaluator or DeterministicEvaluator(), max_questions=5
    )
    settings = Settings(
        merit_storage_mode="memory",
        gemini_api_key="",
        _env_file=None,
    )
    client = TestClient(create_app(service=service, settings=settings))
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "demo", "password": "MeritDemo@2026"},
    )
    assert response.status_code == 200
    return client


def test_demo_login_logout_and_protected_routes():
    service = AssessmentService(
        MemoryAssessmentRepository(), DeterministicEvaluator(), max_questions=5
    )
    settings = Settings(merit_storage_mode="memory", gemini_api_key="", _env_file=None)
    client = TestClient(create_app(service=service, settings=settings))

    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/assessment-methodology").status_code == 401
    assert client.post(
        "/api/v1/auth/login", json={"username": "demo", "password": "wrong"}
    ).status_code == 401

    logged_in = client.post(
        "/api/v1/auth/login",
        json={"username": "demo", "password": "MeritDemo@2026"},
    )
    assert logged_in.status_code == 200
    assert "HttpOnly" in logged_in.headers["set-cookie"]
    assert client.get("/api/v1/auth/me").json() == {"username": "demo"}
    assert client.get("/api/v1/assessment-methodology").status_code == 200

    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_signup_creates_a_session_and_accounts_are_isolated():
    service = AssessmentService(
        MemoryAssessmentRepository(), DeterministicEvaluator(), max_questions=5
    )
    settings = Settings(merit_storage_mode="memory", gemini_api_key="", _env_file=None)
    client = TestClient(create_app(service=service, settings=settings))

    first = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Maya Singh",
            "email": "maya@example.com",
            "password": "SecurePass123!",
            "confirm_password": "SecurePass123!",
        },
    )
    assert first.status_code == 201
    assert first.json()["email"] == "maya@example.com"
    assert client.get("/api/v1/auth/me").json()["username"] == "maya@example.com"

    started = client.post(
        "/api/v1/assessments",
        json={
            "candidate": {
                "name": "Maya Singh",
                "experience_level": "fresher",
                "target_role": "Mechanical Engineer",
            }
        },
    )
    assert started.status_code == 201
    assessment_id = started.json()["assessment_id"]
    client.post("/api/v1/auth/logout")

    second = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Arun Rao",
            "email": "arun@example.com",
            "password": "AnotherPass123!",
            "confirm_password": "AnotherPass123!",
        },
    )
    assert second.status_code == 201
    assert client.get(f"/api/v1/assessments/{assessment_id}").status_code == 404

    client.post("/api/v1/auth/logout")
    logged_back_in = client.post(
        "/api/v1/auth/login",
        json={"username": "maya@example.com", "password": "SecurePass123!"},
    )
    assert logged_back_in.status_code == 200
    assert client.get(f"/api/v1/assessments/{assessment_id}").status_code == 200


def test_signup_validation_and_duplicate_account_errors():
    service = AssessmentService(
        MemoryAssessmentRepository(), DeterministicEvaluator(), max_questions=5
    )
    settings = Settings(merit_storage_mode="memory", gemini_api_key="", _env_file=None)
    client = TestClient(create_app(service=service, settings=settings))

    mismatched = client.post(
        "/api/v1/auth/signup",
        json={
            "name": "Maya Singh",
            "email": "maya@example.com",
            "password": "SecurePass123!",
            "confirm_password": "different-password",
        },
    )
    assert mismatched.status_code == 422

    payload = {
        "name": "Maya Singh",
        "email": "maya@example.com",
        "password": "SecurePass123!",
        "confirm_password": "SecurePass123!",
    }
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 201
    client.post("/api/v1/auth/logout")
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 409


def test_candidate_profile_persists_for_the_logged_in_account():
    client = make_client()
    assert client.get("/api/v1/profile").status_code == 404

    draft = {
        "form_values": {
            "name": "Maya Singh",
            "email": "maya@example.com",
            "education": "B.Tech Computer Science",
            "graduation_year": "2026",
            "experience_level": "fresher",
            "target_role": "AI Engineer",
            "skills": "Python, FastAPI",
        },
        "resume_profile": None,
        "resume_context_text": None,
        "resume_name": None,
        "candidate": {
            "name": "Maya Singh",
            "email": "maya@example.com",
            "education": "B.Tech Computer Science",
            "graduation_year": 2026,
            "experience_level": "fresher",
            "target_role": "AI Engineer",
            "technical_skills": ["Python", "FastAPI"],
            "projects": [],
        },
    }
    saved = client.put("/api/v1/profile", json=draft)
    assert saved.status_code == 200
    assert saved.json()["candidate"]["target_role"] == "AI Engineer"

    restored = client.get("/api/v1/profile")
    assert restored.status_code == 200
    assert restored.json()["form_values"]["skills"] == "Python, FastAPI"

    active_id = "3e449aef-8931-4832-9a36-0e22277531b8"
    with_active = client.put(
        "/api/v1/profile",
        json={
            **draft,
            "active_assessment_id": active_id,
            "active_question_remaining_seconds": 123,
        },
    )
    assert with_active.json()["active_assessment_id"] == active_id
    assert with_active.json()["active_question_remaining_seconds"] == 123

    edited_without_active_field = client.put("/api/v1/profile", json=draft)
    assert edited_without_active_field.json()["active_assessment_id"] == active_id
    assert edited_without_active_field.json()["active_question_remaining_seconds"] == 123

    cleared = client.put(
        "/api/v1/profile",
        json={
            **draft,
            "active_assessment_id": None,
            "active_question_remaining_seconds": None,
        },
    )
    assert cleared.json()["active_assessment_id"] is None


def test_health_and_complete_http_workflow():
    client = make_client()
    assert client.get("/health").json()["status"] == "ok"

    started = client.post(
        "/api/v1/assessments",
        json={
            "candidate": {
                "name": "Maya Singh",
                "experience_level": "fresher",
                "target_role": "AI Engineer",
                "technical_skills": ["Python", "React"],
                "projects": [
                    {
                        "name": "Issue triage tool",
                        "description": "Routes support issues using a FastAPI service.",
                        "technologies": ["FastAPI", "React"],
                    }
                ],
            }
        },
    )
    assert started.status_code == 201
    payload = started.json()
    assessment_id = payload["assessment_id"]

    while payload.get("question"):
        response = client.post(
            f"/api/v1/assessments/{assessment_id}/responses",
            json={
                "question_id": payload["question"]["id"],
                "content": (
                    "I use data flow, validation, logs and evidence to reproduce issues, rank "
                    "hypotheses, make a safe fix, and verification through tests. I define scope, "
                    "security, limitations, an incremental plan and acceptance criteria."
                ),
            },
        )
        assert response.status_code == 200, response.text
        payload = response.json()

    assert payload["status"] == "completed"
    result = client.get(f"/api/v1/assessments/{assessment_id}/result")
    assert result.status_code == 200
    assert result.json()["evidence_summary"]


def test_local_frontend_origins_are_allowed():
    client = make_client()
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        response = client.options(
            "/api/v1/assessments",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_api_landing_explains_where_to_go():
    response = make_client().get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Merit AI Assessment API is running.",
        "frontend": "http://localhost:5173",
        "swagger_docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "resume_parser": "/api/v1/resumes/parse",
    }


def test_resume_parse_route_returns_only_extracted_fields():
    class FakeResumeParser:
        def parse(self, filename: str, content: bytes) -> ResumeParseResponse:
            assert filename == "candidate.txt"
            assert b"Maya Singh" in content
            return ResumeParseResponse(
                filename=filename,
                profile=ResumeProfile(
                    name="Maya Singh",
                    email="maya@example.com",
                    technical_skills=["Python", "FastAPI"],
                ),
                extracted_fields=["name", "email", "technical_skills"],
                warnings=["Target role was not stated in the resume."],
                parser_model="test-parser",
                context_text="Maya Singh\nmaya@example.com\nPython and FastAPI engineer profile.",
            )

    client = make_client()
    client.app.state.resume_parser = FakeResumeParser()
    response = client.post(
        "/api/v1/resumes/parse",
        files={
            "file": (
                "candidate.txt",
                b"Maya Singh\nmaya@example.com\nPython and FastAPI engineer profile.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["name"] == "Maya Singh"
    assert payload["profile"]["target_role"] is None
    assert payload["extracted_fields"] == ["name", "email", "technical_skills"]


def test_resume_work_context_personalizes_the_first_question():
    client = make_client()
    response = client.post(
        "/api/v1/assessments",
        json={
            "candidate": {
                "name": "Maya Singh",
                "experience_level": "2-5 years",
                "target_role": "Backend Engineer",
                "technical_skills": ["Python", "FastAPI"],
                "resume_context": {
                    "professional_summary": "Backend engineer focused on reliable APIs.",
                    "work_experience": [
                        {
                            "title": "Software Engineer",
                            "company": "Acme Labs",
                            "description": "Built a support-routing service.",
                            "achievements": ["Reduced routing time by 40%."],
                            "technologies": ["Python", "FastAPI"],
                        }
                    ],
                    "achievements": ["Won the internal reliability award."],
                    "certifications": [],
                    "additional_context": [],
                    "source_filename": "maya.pdf",
                },
            }
        },
    )

    assert response.status_code == 201
    question = response.json()["question"]
    assert question["prompt"].startswith("Tell me about yourself")
    assert question["assessment_area"] == "introduction"
    assert question["time_limit_seconds"] in {120, 180, 300}


def test_methodology_and_openapi_explain_the_engine():
    client = make_client()
    methodology = client.get("/api/v1/assessment-methodology")
    assert methodology.status_code == 200
    payload = methodology.json()
    assert payload["dimensions"] == []
    assert payload["practical_challenge_enabled"] is False
    assert any("role-specific stretch" in rule for rule in payload["stopping_rules"])

    schema = client.get("/openapi.json").json()
    submit = schema["paths"]["/api/v1/assessments/{assessment_id}/responses"]["post"]
    assert submit["operationId"] == "submitAssessmentResponse"
    assert "idempotent" in submit["description"]
    assert {"400", "404", "409", "422", "503"}.issubset(submit["responses"])


def test_evaluator_quota_error_is_retryable_without_losing_state():
    class UnavailableEvaluator(DeterministicEvaluator):
        model_name = "unavailable-test-model"

        def evaluate(self, candidate, question, response_text):
            del candidate, question, response_text
            raise EvaluationUnavailableError(retry_after_seconds=49)

    client = make_client(UnavailableEvaluator())
    started = client.post(
        "/api/v1/assessments",
        json={
            "candidate": {
                "name": "Quota Test",
                "experience_level": "fresher",
                "target_role": "AI Engineer",
            }
        },
    ).json()
    response = client.post(
        f"/api/v1/assessments/{started['assessment_id']}/responses",
        json={"question_id": started["question"]["id"], "content": "A valid answer."},
    )
    assert response.status_code == 503
    assert response.headers["retry-after"] == "49"

    resumed = client.get(f"/api/v1/assessments/{started['assessment_id']}").json()
    assert resumed["questions_answered"] == 0
    assert resumed["question"]["id"] == started["question"]["id"]


def test_offline_evidence_fallback_keeps_assessment_moving_when_ai_is_down():
    class UnavailableEvaluator(DeterministicEvaluator):
        model_name = "unavailable-provider"

        def plan_assessment(self, candidate):
            del candidate
            raise EvaluationUnavailableError()

        def evaluate(self, candidate, question, response_text):
            del candidate, question, response_text
            raise EvaluationUnavailableError()

        def generate_question(self, candidate, blueprint, dimension, history, action, focus):
            del candidate, blueprint, dimension, history, action, focus
            raise EvaluationUnavailableError()

    evaluator = FallbackEvaluator(
        UnavailableEvaluator(),
        OfflineEvidenceEvaluator(),
        primary_timeout=1,
        fallback_timeout=1,
        cooldown_seconds=1,
    )
    client = make_client(evaluator)
    started = client.post(
        "/api/v1/assessments",
        json={
            "candidate": {
                "name": "Offline Candidate",
                "experience_level": "fresher",
                "target_role": "Mechanical Engineer",
            }
        },
    )
    assert started.status_code == 201

    state = started.json()
    submitted = client.post(
        f"/api/v1/assessments/{state['assessment_id']}/responses",
        json={
            "question_id": state["question"]["id"],
            "content": "I designed a fixture, tested tolerances, and verified the result.",
        },
    )
    assert submitted.status_code == 200
    assert submitted.json()["progress"] > 0
    assert submitted.json()["question"] is not None

    resumed = client.get(f"/api/v1/assessments/{state['assessment_id']}").json()
    assert resumed["questions_answered"] == 1


def test_long_generated_questions_are_compacted_for_candidates():
    long_prompt = " ".join(
        ["A detailed personalized scenario contains many unnecessary setup words"] * 10
    )
    prompt = concise_prompt(long_prompt)

    assert len(prompt.split()) <= 38
    assert prompt.endswith("how would you verify the result?")
