from dataclasses import dataclass

from app.assessment.models import Dimension


@dataclass(frozen=True)
class DimensionRubric:
    purpose: str
    strong_signals: tuple[str, ...]
    weak_signals: tuple[str, ...]
    weight: float


RUBRICS: dict[Dimension, DimensionRubric] = {
    Dimension.ENGINEERING_FUNDAMENTALS: DimensionRubric(
        purpose="Assess whether the candidate understands how software systems work end to end.",
        strong_signals=(
            "clear component boundaries and data flow",
            "validation and error handling",
            "security and data integrity",
            "testing and observability",
        ),
        weak_signals=("buzzwords without mechanisms", "ignores failure modes", "unclear ownership"),
        weight=0.25,
    ),
    Dimension.PROBLEM_SOLVING: DimensionRubric(
        purpose="Assess structured diagnosis, prioritization, trade-offs, and verification.",
        strong_signals=(
            "forms and ranks hypotheses",
            "uses evidence to narrow the problem",
            "chooses a low-risk intervention",
            "verifies the outcome",
        ),
        weak_signals=("jumps to a fix", "no reproduction", "no verification"),
        weight=0.22,
    ),
    Dimension.AI_FLUENCY: DimensionRubric(
        purpose="Assess appropriate, safe, and effective use of AI in engineering work.",
        strong_signals=(
            "uses AI for suitable non-deterministic tasks",
            "provides context and constraints",
            "recognizes model limitations",
            "protects sensitive information",
        ),
        weak_signals=("blind trust", "vague prompting", "uses AI for deterministic control logic"),
        weight=0.17,
    ),
    Dimension.AGENTIC_ENGINEERING: DimensionRubric(
        purpose="Assess agent delegation with explicit validation and completion criteria.",
        strong_signals=(
            "clear task boundaries and constraints",
            "incremental implementation plan",
            "tests and observable acceptance criteria",
            "reviews artifacts rather than trusting claims",
        ),
        weak_signals=("one-shot delegation", "no tests", "no rollback or review strategy"),
        weight=0.23,
    ),
    Dimension.COMMUNICATION: DimensionRubric(
        purpose="Assess clarity, structure, precision, and audience awareness.",
        strong_signals=(
            "direct answer",
            "logical structure",
            "specific examples",
            "states assumptions and trade-offs",
        ),
        weak_signals=("rambling", "ambiguous claims", "unsupported conclusions"),
        weight=0.13,
    ),
}


DIMENSION_ORDER = list(RUBRICS)
