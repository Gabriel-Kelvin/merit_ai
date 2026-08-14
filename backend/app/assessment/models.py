from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class Dimension(StrEnum):
    ENGINEERING_FUNDAMENTALS = "engineering_fundamentals"
    PROBLEM_SOLVING = "problem_solving"
    AI_FLUENCY = "ai_fluency"
    AGENTIC_ENGINEERING = "agentic_engineering"
    COMMUNICATION = "communication"


DIMENSION_LABELS: dict[Dimension, str] = {
    Dimension.ENGINEERING_FUNDAMENTALS: "Engineering Fundamentals",
    Dimension.PROBLEM_SOLVING: "Problem Solving",
    Dimension.AI_FLUENCY: "AI Fluency",
    Dimension.AGENTIC_ENGINEERING: "Agentic Engineering",
    Dimension.COMMUNICATION: "Communication",
}


class QuestionType(StrEnum):
    TEXT = "text"
    SCENARIO = "scenario"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    AGENT_INSTRUCTION = "agent_instruction"


class Difficulty(StrEnum):
    FOUNDATION = "foundation"
    STANDARD = "standard"
    ADVANCED = "advanced"


class SignalStatus(StrEnum):
    DEMONSTRATED = "demonstrated"
    PARTIAL = "partial"
    MISSING = "missing"
    CONTRADICTED = "contradicted"


class AdaptiveAction(StrEnum):
    PROBE_GAP = "probe_gap"
    STRETCH = "stretch"
    ADVANCE = "advance"
    COMPLETE = "complete"
    REPLAY = "replay"


class AssessmentStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReadinessClassification(StrEnum):
    READY = "READY"
    TARGETED_DEVELOPMENT = "TARGETED_DEVELOPMENT"
    STRUCTURED_DEVELOPMENT = "STRUCTURED_DEVELOPMENT"
    FOUNDATION_DEVELOPMENT = "FOUNDATION_DEVELOPMENT"


class ProjectExperience(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=10, max_length=1000)
    technologies: list[str] = Field(default_factory=list, max_length=20)


class CandidateContext(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Maya Singh",
                "email": "maya@example.com",
                "education": "B.Tech Computer Science",
                "graduation_year": 2026,
                "experience_level": "fresher",
                "target_role": "AI Engineer",
                "technical_skills": ["Python", "FastAPI", "React", "PostgreSQL"],
                "projects": [
                    {
                        "name": "Issue triage assistant",
                        "description": "A React and FastAPI tool that routes support issues.",
                        "technologies": ["React", "FastAPI", "PostgreSQL"],
                    }
                ],
                "ai_tools_used": ["Gemini", "Codex"],
            }
        }
    )
    name: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    education: str | None = Field(default=None, max_length=300)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    experience_level: str = Field(min_length=2, max_length=80)
    target_role: str = Field(min_length=2, max_length=120)
    technical_skills: list[str] = Field(default_factory=list, max_length=30)
    projects: list[ProjectExperience] = Field(default_factory=list, max_length=10)
    ai_tools_used: list[str] = Field(default_factory=list, max_length=20)
    github_url: HttpUrl | None = None
    linkedin_url: HttpUrl | None = None

    @field_validator("technical_skills", "ai_tools_used")
    @classmethod
    def normalize_list(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class Question(BaseModel):
    id: UUID
    sequence_no: int = Field(ge=1)
    dimension: Dimension
    type: QuestionType
    difficulty: Difficulty
    prompt: str
    intent: str
    expected_signals: list[str] = Field(default_factory=list)
    personalization_context: str | None = None
    is_follow_up: bool = False
    parent_question_id: UUID | None = None
    adaptation_reason: str = "Initial capability probe"


class EvidenceItem(BaseModel):
    claim: str = Field(description="A concise capability claim supported by the answer.")
    support: str = Field(description="A short paraphrase of the answer that supports the claim.")
    strength: Literal["strong", "moderate", "weak", "missing"]
    signal: str | None = Field(
        default=None, description="The rubric signal this evidence supports or fails to support."
    )


class SignalAssessment(BaseModel):
    signal: str
    status: SignalStatus
    explanation: str = Field(
        description="A short, answer-grounded explanation of the signal verdict."
    )


class ResponseEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=6)
    strengths: list[str] = Field(default_factory=list, max_length=4)
    gaps: list[str] = Field(default_factory=list, max_length=4)
    follow_up_required: bool
    follow_up_focus: str | None = Field(default=None, max_length=120)
    signal_assessments: list[SignalAssessment] = Field(default_factory=list)
    answer_relevance: float = Field(default=1.0, ge=0, le=1)
    integrity_flags: list[str] = Field(default_factory=list, max_length=4)
    reasoning_summary: str = Field(
        description="A concise assessor explanation without hidden chain-of-thought."
    )


class AdaptiveDecision(BaseModel):
    action: AdaptiveAction
    reason: str
    targeted_signal: str | None = None
    evidence_sufficient: bool


class DimensionProgress(BaseModel):
    dimension: Dimension
    questions_answered: int = Field(ge=0)
    credible_evidence_count: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    evidence_sufficient: bool


class DimensionScore(BaseModel):
    dimension: Dimension
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence_count: int = Field(ge=0)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evidence_quality: int = Field(default=0, ge=0, le=100)
    confidence_label: str = "Low"
    rationale: str = "Insufficient evidence collected."
    limiting_gap: str | None = None


class EvaluationTraceItem(BaseModel):
    question_id: UUID
    sequence_no: int
    dimension: Dimension
    difficulty: Difficulty
    question: str
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    pathway: ReadinessClassification
    title: str
    rationale: str
    priority_capabilities: list[str]
    next_actions: list[str]
    top_development_priority: str
    why: str
    proof_of_improvement_challenge: str | None = Field(
        default=None,
        description="Reserved for a future practical-challenge module; currently disabled.",
    )


class AssessmentResult(BaseModel):
    assessment_id: UUID
    readiness_score: int = Field(ge=0, le=100)
    classification: ReadinessClassification
    dimensions: list[DimensionScore]
    strengths: list[str]
    gaps: list[str]
    evidence_summary: list[EvidenceItem]
    evaluation_trace: list[EvaluationTraceItem] = Field(default_factory=list)
    summary: str
    recommendation: Recommendation
    overall_confidence: float = Field(default=0, ge=0, le=1)
    confidence_label: str = "Low"
    assessment_version: str = "merit-v2"
    rubric_version: str = "rubric-v2"
    prompt_version: str = "assessment-v2"
    model: str


class EvaluationRecord(BaseModel):
    question: Question
    response_text: str
    evaluation: ResponseEvaluation


class AssessmentSession(BaseModel):
    id: UUID
    candidate: CandidateContext
    status: AssessmentStatus = AssessmentStatus.IN_PROGRESS
    current_question: Question | None = None
    records: list[EvaluationRecord] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    followups_used: dict[str, int] = Field(default_factory=dict)
    max_questions: int = Field(default=7, ge=3, le=12)
    result: AssessmentResult | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def progress(self) -> int:
        if self.status == AssessmentStatus.COMPLETED:
            return 100
        return min(95, round(len(self.records) / self.max_questions * 100))


class StartAssessmentRequest(BaseModel):
    candidate: CandidateContext


class StartAssessmentResponse(BaseModel):
    assessment_id: UUID
    status: AssessmentStatus
    progress: int
    question: Question
    max_questions: int
    assessment_version: str = "merit-v2"


class SubmitResponseRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question_id": "ef9dd596-f13f-4ee8-a195-7436186ad813",
                "content": (
                    "The browser validates required fields, then sends JSON to FastAPI. The API "
                    "validates the schema and writes inside a transaction. A uniqueness constraint "
                    "prevents duplicate records, and an integration test verifies the failure path."
                ),
            }
        }
    )
    question_id: UUID
    content: str = Field(min_length=3, max_length=8000)


class SubmitResponseResponse(BaseModel):
    assessment_id: UUID
    status: AssessmentStatus
    progress: int
    evaluation: ResponseEvaluation
    adaptive_decision: AdaptiveDecision
    question: Question | None = None
    result: AssessmentResult | None = None
    replayed: bool = False


class AssessmentStateResponse(BaseModel):
    assessment_id: UUID
    status: AssessmentStatus
    progress: int
    candidate: CandidateContext
    question: Question | None = None
    questions_answered: int
    max_questions: int
    dimension_progress: list[DimensionProgress] = Field(default_factory=list)
    result: AssessmentResult | None = None


class ErrorResponse(BaseModel):
    detail: str


class MethodologyDimension(BaseModel):
    dimension: Dimension
    label: str
    purpose: str
    weight: float
    strong_signals: list[str]
    weak_signals: list[str]


class AssessmentMethodologyResponse(BaseModel):
    assessment_version: str = "merit-v2"
    rubric_version: str = "rubric-v2"
    prompt_version: str = "assessment-v2"
    principles: list[str]
    stopping_rules: list[str]
    dimensions: list[MethodologyDimension]
    practical_challenge_enabled: bool = False
