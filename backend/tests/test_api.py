from fastapi.testclient import TestClient

from app.assessment.evaluator import DeterministicEvaluator, EvaluationUnavailableError
from app.assessment.service import AssessmentService
from app.config import Settings
from app.main import create_app
from app.repositories.memory import MemoryAssessmentRepository


def make_client(evaluator=None) -> TestClient:
    service = AssessmentService(
        MemoryAssessmentRepository(), evaluator or DeterministicEvaluator(), max_questions=5
    )
    settings = Settings(
        merit_storage_mode="memory",
        gemini_api_key="",
        _env_file=None,
    )
    return TestClient(create_app(service=service, settings=settings))


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


def test_methodology_and_openapi_explain_the_engine():
    client = make_client()
    methodology = client.get("/api/v1/assessment-methodology")
    assert methodology.status_code == 200
    payload = methodology.json()
    assert len(payload["dimensions"]) == 5
    assert payload["practical_challenge_enabled"] is False
    assert any("higher-difficulty" in rule for rule in payload["stopping_rules"])

    schema = client.get("/openapi.json").json()
    submit = schema["paths"]["/api/v1/assessments/{assessment_id}/responses"]["post"]
    assert submit["operationId"] == "submitAssessmentResponse"
    assert "idempotent" in submit["description"]
    assert {"400", "404", "409", "422", "503"}.issubset(submit["responses"])


def test_evaluator_quota_error_is_retryable_without_losing_state():
    class UnavailableEvaluator:
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
