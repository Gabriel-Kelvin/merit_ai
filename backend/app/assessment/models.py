from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


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


class EvidenceItem(BaseModel):
    claim: str = Field(description="A concise capability claim supported by the answer.")
    support: str = Field(description="A short paraphrase of the answer that supports the claim.")
    strength: str = Field(description="One of: strong, moderate, weak, missing.")


class ResponseEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=6)
    strengths: list[str] = Field(default_factory=list, max_length=4)
    gaps: list[str] = Field(default_factory=list, max_length=4)
    follow_up_required: bool
    follow_up_focus: str | None = None
    reasoning_summary: str = Field(
        description="A concise assessor explanation without hidden chain-of-thought."
    )


class DimensionScore(BaseModel):
    dimension: Dimension
    score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    evidence_count: int = Field(ge=0)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    pathway: ReadinessClassification
    title: str
    rationale: str
    priority_capabilities: list[str]
    next_actions: list[str]
    proof_of_improvement_challenge: str


class AssessmentResult(BaseModel):
    assessment_id: UUID
    readiness_score: int = Field(ge=0, le=100)
    classification: ReadinessClassification
    dimensions: list[DimensionScore]
    strengths: list[str]
    gaps: list[str]
    evidence_summary: list[EvidenceItem]
    summary: str
    recommendation: Recommendation
    assessment_version: str = "merit-v1"
    rubric_version: str = "rubric-v1"
    prompt_version: str = "assessment-v1"
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


class SubmitResponseRequest(BaseModel):
    question_id: UUID
    content: str = Field(min_length=3, max_length=8000)


class SubmitResponseResponse(BaseModel):
    assessment_id: UUID
    status: AssessmentStatus
    progress: int
    evaluation: ResponseEvaluation
    question: Question | None = None
    result: AssessmentResult | None = None


class AssessmentStateResponse(BaseModel):
    assessment_id: UUID
    status: AssessmentStatus
    progress: int
    candidate: CandidateContext
    question: Question | None = None
    questions_answered: int
    result: AssessmentResult | None = None
