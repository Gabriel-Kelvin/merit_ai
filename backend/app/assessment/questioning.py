from __future__ import annotations

from uuid import uuid4

from app.assessment.models import (
    AssessmentSession,
    Difficulty,
    Dimension,
    Question,
    QuestionType,
    ResponseEvaluation,
)
from app.assessment.rubric import DIMENSION_ORDER


class QuestionPlanner:
    """Controls assessment structure; the model never decides the overall workflow."""

    def first_question(self, session: AssessmentSession) -> Question:
        candidate = session.candidate
        if candidate.projects:
            project = candidate.projects[0]
            prompt = (
                f"You mentioned building {project.name}. Walk me through one important request "
                "from the user action to the final stored or displayed result. Explain validation, "
                "failure handling, and how you verified it worked."
            )
        else:
            skills = ", ".join(candidate.technical_skills[:3]) or "your preferred stack"
            prompt = (
                f"Using {skills}, describe how you would build a small production API for "
                "submitting and storing a form. Cover validation, failure handling, and testing."
            )
        return self._question(
            session,
            Dimension.ENGINEERING_FUNDAMENTALS,
            QuestionType.TEXT,
            Difficulty.STANDARD,
            prompt,
            "Establish credible end-to-end engineering evidence from the candidate's own context.",
            ["data flow", "validation", "failure handling", "verification"],
        )

    def next_question(
        self, session: AssessmentSession, evaluation: ResponseEvaluation
    ) -> Question | None:
        current = session.current_question
        if current is None or len(session.records) >= session.max_questions:
            return None

        dimension_key = current.dimension.value
        used = session.followups_used.get(dimension_key, 0)
        current_index = DIMENSION_ORDER.index(current.dimension)
        base_dimensions_remaining = len(DIMENSION_ORDER) - current_index - 1
        question_slots_remaining = session.max_questions - len(session.records)
        can_follow_up_without_losing_coverage = question_slots_remaining > base_dimensions_remaining
        if (
            evaluation.follow_up_required
            and evaluation.score < 70
            and used < 1
            and can_follow_up_without_losing_coverage
        ):
            session.followups_used[dimension_key] = used + 1
            focus = evaluation.follow_up_focus or (
                evaluation.gaps[0] if evaluation.gaps else "depth"
            )
            return self._follow_up(session, current.dimension, focus)

        if current_index + 1 >= len(DIMENSION_ORDER):
            return None
        return self._base_question(session, DIMENSION_ORDER[current_index + 1])

    def _base_question(self, session: AssessmentSession, dimension: Dimension) -> Question:
        role = session.candidate.target_role
        if dimension == Dimension.PROBLEM_SOLVING:
            return self._question(
                session,
                dimension,
                QuestionType.DEBUGGING,
                Difficulty.STANDARD,
                "A feature worked yesterday, but today some users receive duplicate records while "
                "others receive a timeout. Explain how you would investigate this systematically "
                "before changing code, and how you would verify the final fix.",
                "Test hypothesis-driven debugging and verification rather than guesswork.",
                [
                    "reproduction",
                    "logs and evidence",
                    "ranked hypotheses",
                    "safe fix",
                    "verification",
                ],
            )
        if dimension == Dimension.AI_FLUENCY:
            return self._question(
                session,
                dimension,
                QuestionType.SCENARIO,
                Difficulty.STANDARD,
                f"You are using an AI assistant while building a {role} feature. Which parts would "
                "you delegate to AI, which would you keep deterministic, and what would you verify "
                "before accepting the output?",
                "Distinguish useful AI reasoning from deterministic application responsibilities.",
                ["appropriate delegation", "limitations", "security", "verification"],
            )
        if dimension == Dimension.AGENTIC_ENGINEERING:
            return self._question(
                session,
                dimension,
                QuestionType.AGENT_INSTRUCTION,
                Difficulty.ADVANCED,
                "A developer tells a coding agent: ‘Build login.’ Rewrite that instruction "
                "so the agent can implement it safely and prove it is complete. Include context, "
                "constraints, tests, and acceptance criteria.",
                "Measure whether the candidate can direct and verify an autonomous coding agent.",
                [
                    "scope",
                    "security constraints",
                    "incremental plan",
                    "tests",
                    "acceptance criteria",
                ],
            )
        return self._question(
            session,
            Dimension.COMMUNICATION,
            QuestionType.TEXT,
            Difficulty.STANDARD,
            "Explain to a non-technical product manager why an AI-generated feature should not be "
            "released after the code compiles. Keep your answer concise and actionable.",
            "Assess audience-aware technical communication.",
            ["plain language", "risk", "verification", "clear recommendation"],
        )

    def _follow_up(self, session: AssessmentSession, dimension: Dimension, focus: str) -> Question:
        prompts = {
            Dimension.ENGINEERING_FUNDAMENTALS: (
                f"Your previous answer needs stronger evidence around {focus}. Pick one realistic "
                "failure in that flow and explain how you would prevent, detect, and test it."
            ),
            Dimension.PROBLEM_SOLVING: (
                f"Go deeper on {focus}. What exact evidence would distinguish your two most likely "
                "hypotheses, and what result would make you change direction?"
            ),
            Dimension.AI_FLUENCY: (
                f"Clarify {focus}. Give one concrete example where AI output looks convincing but "
                "must be rejected, and describe your verification method."
            ),
            Dimension.AGENTIC_ENGINEERING: (
                f"Strengthen your plan around {focus}. What artifacts must the agent produce, and "
                "what objective checks must pass before you accept the work?"
            ),
            Dimension.COMMUNICATION: (
                f"Your answer needs more clarity around {focus}. Restate it as three short points: "
                "the risk, the required action, and the proof that the action worked."
            ),
        }
        return self._question(
            session,
            dimension,
            QuestionType.TEXT,
            Difficulty.STANDARD,
            prompts[dimension],
            f"Collect missing evidence about {focus}.",
            [focus, "specific example", "verification"],
        )

    @staticmethod
    def _question(
        session: AssessmentSession,
        dimension: Dimension,
        question_type: QuestionType,
        difficulty: Difficulty,
        prompt: str,
        intent: str,
        expected_signals: list[str],
    ) -> Question:
        return Question(
            id=uuid4(),
            sequence_no=len(session.questions) + 1,
            dimension=dimension,
            type=question_type,
            difficulty=difficulty,
            prompt=prompt,
            intent=intent,
            expected_signals=expected_signals,
        )
