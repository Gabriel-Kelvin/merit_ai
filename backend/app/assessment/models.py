from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    CHANGE_TOPIC = "change_topic"


class AssessmentArea(StrEnum):
    INTRODUCTION = "introduction"
    EXPERIENCE = "experience"
    PROJECT = "project"
    ROLE_CAPABILITY = "role_capability"
    PROFESSIONAL_JUDGMENT = "professional_judgment"


class CandidateIntent(StrEnum):
    ANSWER = "answer"
    UNKNOWN = "unknown"
    CHANGE_TOPIC = "change_topic"


class SubmissionReason(StrEnum):
    MANUAL = "manual"
    TIME_EXPIRED = "time_expired"


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


class ResumeWorkContext(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    start_date: str | None = Field(default=None, max_length=40)
    end_date: str | None = Field(default=None, max_length=40)
    description: str | None = Field(default=None, max_length=1200)
    achievements: list[str] = Field(default_factory=list, max_length=8)
    technologies: list[str] = Field(default_factory=list, max_length=20)


class ResumeContext(BaseModel):
    professional_summary: str | None = Field(default=None, max_length=1200)
    work_experience: list[ResumeWorkContext] = Field(default_factory=list, max_length=8)
    achievements: list[str] = Field(default_factory=list, max_length=12)
    certifications: list[str] = Field(default_factory=list, max_length=12)
    additional_context: list[str] = Field(default_factory=list, max_length=12)
    source_filename: str | None = Field(default=None, max_length=255)
    source_text: str | None = Field(
        default=None,
        max_length=12_000,
        description="Readable resume context supplied to the assessment engine.",
    )


class CapabilityDimension(BaseModel):
    id: str = Field(
        min_length=2,
        max_length=60,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Stable role-specific capability identifier generated for this assessment.",
    )
    label: str = Field(min_length=2, max_length=100)
    purpose: str = Field(min_length=10, max_length=500)
    strong_signals: list[str] = Field(min_length=3, max_length=8)
    weak_signals: list[str] = Field(default_factory=list, max_length=6)
    weight: float = Field(ge=0.1, le=0.5)


class AssessmentBlueprint(BaseModel):
    role_family: str = Field(min_length=2, max_length=120)
    rationale: str = Field(min_length=10, max_length=800)
    dimensions: list[CapabilityDimension] = Field(min_length=3, max_length=6)

    @field_validator("dimensions")
    @classmethod
    def normalize_dimensions(
        cls, dimensions: list[CapabilityDimension]
    ) -> list[CapabilityDimension]:
        if len({item.id for item in dimensions}) != len(dimensions):
            raise ValueError("Capability dimension ids must be unique")
        total = sum(item.weight for item in dimensions)
        if not 0.95 <= total <= 1.05:
            raise ValueError("Capability dimension weights must total approximately 1.0")
        return [item.model_copy(update={"weight": item.weight / total}) for item in dimensions]


class GeneratedQuestion(BaseModel):
    type: QuestionType
    difficulty: Difficulty
    prompt: str = Field(min_length=20, max_length=1600)
    intent: str = Field(min_length=10, max_length=500)
    expected_signals: list[str] = Field(min_length=2, max_length=8)
    personalization_context: str | None = Field(default=None, max_length=1000)
    time_limit_seconds: int = Field(
        default=180,
        ge=120,
        le=300,
        description="AI-selected answer window: 2, 3, or 5 minutes.",
    )

    @field_validator("time_limit_seconds")
    @classmethod
    def normalize_time_limit(cls, value: int) -> int:
        return min((120, 180, 300), key=lambda allowed: abs(allowed - value))


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
    resume_context: ResumeContext | None = Field(
        default=None,
        description=(
            "Structured evidence retained from the uploaded resume for question personalization; "
            "the raw resume file is not stored."
        ),
    )

    @field_validator("technical_skills")
    @classmethod
    def normalize_list(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class Question(BaseModel):
    id: UUID
    sequence_no: int = Field(ge=1)
    dimension: str = Field(min_length=2, max_length=60, pattern=r"^[a-z][a-z0-9_]*$")
    dimension_label: str = Field(min_length=2, max_length=100)
    type: QuestionType
    difficulty: Difficulty
    prompt: str
    intent: str
    expected_signals: list[str] = Field(default_factory=list)
    personalization_context: str | None = None
    is_follow_up: bool = False
    parent_question_id: UUID | None = None
    adaptation_reason: str = "Initial capability probe"
    assessment_area: AssessmentArea = AssessmentArea.ROLE_CAPABILITY
    time_limit_seconds: Literal[120, 180, 300] = 180
    issued_at: datetime | None = None
    expires_at: datetime | None = None


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
    evaluator_model: str | None = Field(
        default=None, description="Server-recorded model that produced this evaluation."
    )
    reasoning_summary: str = Field(
        description="A concise assessor explanation without hidden chain-of-thought."
    )
    candidate_intent: CandidateIntent = CandidateIntent.ANSWER
    requested_topic: str | None = Field(default=None, max_length=120)


class AdaptiveDecision(BaseModel):
    action: AdaptiveAction
    reason: str
    targeted_signal: str | None = None
    evidence_sufficient: bool


class DimensionProgress(BaseModel):
    dimension: str
    label: str
    questions_answered: int = Field(ge=0)
    credible_evidence_count: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    evidence_sufficient: bool


class DimensionScore(BaseModel):
    dimension: str
    label: str
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
    dimension: str
    dimension_label: str
    difficulty: Difficulty
    question: str
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    reasoning_summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    evaluator_model: str | None = None


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
    submission_reason: SubmissionReason = SubmissionReason.MANUAL
    time_spent_seconds: int | None = Field(default=None, ge=0, le=1800)


class AssessmentMemory(BaseModel):
    graph_version: str = "langgraph-v1"
    area_counts: dict[str, int] = Field(default_factory=dict)
    coverage_targets: dict[str, int] = Field(default_factory=dict)
    avoided_topics: list[str] = Field(default_factory=list, max_length=20)
    evidence_gaps: list[str] = Field(default_factory=list, max_length=30)
    conversation_summary: str = Field(default="", max_length=6000)
    last_transition: str = "start"


class AssessmentSession(BaseModel):
    id: UUID
    account_id: str | None = None
    candidate: CandidateContext
    blueprint: AssessmentBlueprint | None = None
    status: AssessmentStatus = AssessmentStatus.IN_PROGRESS
    current_question: Question | None = None
    records: list[EvaluationRecord] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    followups_used: dict[str, int] = Field(default_factory=dict)
    max_questions: int = Field(default=20, ge=3, le=20)
    memory: AssessmentMemory = Field(default_factory=AssessmentMemory)
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
    content: str = Field(default="", max_length=8000)
    submission_reason: SubmissionReason = SubmissionReason.MANUAL
    time_spent_seconds: int | None = Field(default=None, ge=0, le=1800)


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
    memory: AssessmentMemory
    result: AssessmentResult | None = None


class ErrorResponse(BaseModel):
    detail: str


class MethodologyDimension(BaseModel):
    dimension: str
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
