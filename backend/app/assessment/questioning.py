from __future__ import annotations

from uuid import uuid4

from app.assessment.models import (
    AdaptiveAction,
    AdaptiveDecision,
    AssessmentSession,
    Difficulty,
    Dimension,
    Question,
    QuestionType,
    ResponseEvaluation,
)
from app.assessment.rubric import DIMENSION_ORDER


class QuestionPlanner:
    """Deterministic workflow controller around evidence produced by the AI evaluator."""

    sufficiency_confidence = 0.76
    strong_score = 82

    def first_question(self, session: AssessmentSession) -> Question:
        candidate = session.candidate
        if candidate.projects:
            project = candidate.projects[0]
            technology = ", ".join(project.technologies[:3]) or "your chosen stack"
            prompt = (
                f"In your {project.name} project using {technology}, choose one real user action. "
                "Walk me through the request from the interface to the final stored or displayed "
                "result. Be specific about validation, one failure path, and how you verified it."
            )
            context = f"Project: {project.name}; technologies: {technology}"
        else:
            skills = ", ".join(candidate.technical_skills[:3]) or "your preferred stack"
            prompt = (
                f"Using {skills}, explain how you would implement a form submission from the "
                "interface to persistent storage. Include validation, one failure path, and the "
                "tests or observations that would prove it works."
            )
            context = f"Candidate skills: {skills}"
        return self._question(
            session,
            Dimension.ENGINEERING_FUNDAMENTALS,
            QuestionType.TEXT,
            Difficulty.STANDARD,
            prompt,
            "Establish credible end-to-end engineering evidence in the candidate's own context.",
            ["data flow", "validation", "failure handling", "verification"],
            personalization_context=context,
        )

    def next_question(
        self, session: AssessmentSession, evaluation: ResponseEvaluation
    ) -> tuple[Question | None, AdaptiveDecision]:
        current = session.current_question
        if current is None or len(session.records) >= session.max_questions:
            return None, self._complete("The maximum question limit has been reached.")

        used = session.followups_used.get(current.dimension.value, 0)
        current_index = DIMENSION_ORDER.index(current.dimension)
        remaining_dimensions = len(DIMENSION_ORDER) - current_index - 1
        remaining_slots = session.max_questions - len(session.records)
        has_adaptive_slot = remaining_slots > remaining_dimensions
        credible_evidence = sum(
            item.strength in {"strong", "moderate"} for item in evaluation.evidence
        )
        evidence_sufficient = (
            evaluation.confidence >= self.sufficiency_confidence
            and evaluation.answer_relevance >= 0.7
            and credible_evidence >= 2
            and not evaluation.integrity_flags
        )

        if (
            has_adaptive_slot
            and used < 1
            and (
                evaluation.follow_up_required
                or not evidence_sufficient
                or evaluation.score < 65
            )
        ):
            focus = evaluation.follow_up_focus or (
                evaluation.gaps[0] if evaluation.gaps else current.expected_signals[0]
            )
            session.followups_used[current.dimension.value] = used + 1
            question = self._gap_probe(session, current, focus)
            return question, AdaptiveDecision(
                action=AdaptiveAction.PROBE_GAP,
                reason=(
                    f"The answer did not yet provide enough credible evidence about {focus}; "
                    "one focused probe could materially improve confidence."
                ),
                targeted_signal=focus,
                evidence_sufficient=False,
            )

        if (
            has_adaptive_slot
            and used < 1
            and current.dimension == Dimension.ENGINEERING_FUNDAMENTALS
            and evaluation.confidence >= 0.82
            and (
                evaluation.score >= self.strong_score
                or credible_evidence >= len(current.expected_signals)
            )
        ):
            session.followups_used[current.dimension.value] = used + 1
            question = self._stretch_probe(session, current)
            return question, AdaptiveDecision(
                action=AdaptiveAction.STRETCH,
                reason=(
                    "The answer supplied strong, high-confidence fundamentals, so the engine "
                    "increased difficulty to test production depth."
                ),
                targeted_signal="concurrency and data integrity",
                evidence_sufficient=True,
            )

        if current_index + 1 >= len(DIMENSION_ORDER):
            return None, self._complete(
                "Every capability has been covered and no further probe is justified."
            )

        next_dimension = DIMENSION_ORDER[current_index + 1]
        question = self._base_question(session, next_dimension)
        return question, AdaptiveDecision(
            action=AdaptiveAction.ADVANCE,
            reason=(
                "The available evidence is sufficient for this capability, so the assessment "
                f"advanced to {next_dimension.value.replace('_', ' ')}."
            ),
            evidence_sufficient=evidence_sufficient,
        )

    def _base_question(self, session: AssessmentSession, dimension: Dimension) -> Question:
        candidate = session.candidate
        role = candidate.target_role
        project = candidate.projects[0].name if candidate.projects else "a recent project"
        stack = ", ".join(candidate.technical_skills[:3]) or "the candidate's stack"
        if dimension == Dimension.PROBLEM_SOLVING:
            return self._question(
                session,
                dimension,
                QuestionType.DEBUGGING,
                Difficulty.STANDARD,
                f"Imagine {project} starts creating duplicate records for some users and timing "
                "out for others. Before changing code, explain your investigation in order: what "
                "you would reproduce, inspect, compare, change safely, and verify.",
                "Test hypothesis-driven diagnosis and verification rather than guesswork.",
                [
                    "reproduction",
                    "ranked hypotheses",
                    "diagnostic evidence",
                    "safe fix",
                    "verification",
                ],
                personalization_context=f"Candidate project: {project}",
            )
        if dimension == Dimension.AI_FLUENCY:
            tools = ", ".join(candidate.ai_tools_used[:2]) or "an AI assistant"
            return self._question(
                session,
                dimension,
                QuestionType.SCENARIO,
                Difficulty.STANDARD,
                f"While working toward a {role} role with {tools}, which engineering tasks would "
                "you delegate to AI, which decisions must remain deterministic or human-owned, "
                "and how would you detect a convincing but incorrect output?",
                "Measure safe task selection, model awareness, and verification discipline.",
                [
                    "appropriate delegation",
                    "deterministic boundaries",
                    "limitations",
                    "security",
                    "verification",
                ],
                personalization_context=f"Target role: {role}; AI tools: {tools}",
            )
        if dimension == Dimension.AGENTIC_ENGINEERING:
            return self._question(
                session,
                dimension,
                QuestionType.SCENARIO,
                Difficulty.ADVANCED,
                f"You ask a coding agent to add a sensitive feature to a {stack} application. "
                "Describe how you would divide the work, constrain the agent, inspect intermediate "
                "artifacts, handle a failed check, and decide that the work is genuinely complete.",
                "Assess control of agent workflows without requiring a practical IDE exercise.",
                [
                    "task boundaries",
                    "constraints",
                    "incremental review",
                    "failure recovery",
                    "acceptance criteria",
                ],
                personalization_context=f"Candidate stack: {stack}",
            )
        return self._question(
            session,
            Dimension.COMMUNICATION,
            QuestionType.TEXT,
            Difficulty.STANDARD,
            f"A product manager wants to release an AI-assisted feature in {project} because the "
            "code compiles. In a concise message, explain the risk, the checks you require, and "
            "the evidence you would use to approve release.",
            "Assess concise, audience-aware communication with an actionable recommendation.",
            ["plain language", "risk", "required action", "verification evidence"],
            personalization_context=f"Candidate project: {project}",
        )

    def _gap_probe(self, session: AssessmentSession, parent: Question, focus: str) -> Question:
        prompts = {
            Dimension.ENGINEERING_FUNDAMENTALS: (
                f"Your explanation left {focus} unclear. Choose one concrete failure in the flow "
                "you described and explain exactly where it is detected, what the user receives, "
                "what is logged, and the test that proves the behavior."
            ),
            Dimension.PROBLEM_SOLVING: (
                f"Go deeper on {focus}. Name your two leading hypotheses, the exact observation "
                "that distinguishes them, and the result that would make you change direction."
            ),
            Dimension.AI_FLUENCY: (
                f"Your answer needs clearer evidence about {focus}. Give one plausible AI output "
                "you would reject, the risk it creates, and the objective check that exposes it."
            ),
            Dimension.AGENTIC_ENGINEERING: (
                f"Clarify {focus}. If the agent claims it is finished but one check fails, what "
                "artifact do you inspect, what do you ask it to change, and what must pass next?"
            ),
            Dimension.COMMUNICATION: (
                f"Restate your answer with more precision about {focus}: one sentence for the "
                "risk, one for the required action, and one for the evidence of completion."
            ),
        }
        return self._question(
            session,
            parent.dimension,
            QuestionType.TEXT,
            Difficulty.STANDARD,
            prompts[parent.dimension],
            f"Resolve insufficient or ambiguous evidence about {focus}.",
            [focus, "specific mechanism", "objective verification"],
            personalization_context=parent.personalization_context,
            is_follow_up=True,
            parent_question_id=parent.id,
            adaptation_reason=f"Previous evidence was weak or ambiguous around {focus}.",
        )

    def _stretch_probe(self, session: AssessmentSession, parent: Question) -> Question:
        return self._question(
            session,
            parent.dimension,
            QuestionType.SCENARIO,
            Difficulty.ADVANCED,
            "Now increase the difficulty: two identical requests arrive at the same time after a "
            "client retry. Explain how you would prevent duplicate records, preserve consistency, "
            "and verify the behavior under concurrency.",
            "Test production depth after strong fundamental evidence.",
            ["idempotency", "database constraint", "transaction boundary", "concurrency test"],
            personalization_context=parent.personalization_context,
            is_follow_up=True,
            parent_question_id=parent.id,
            adaptation_reason="Strong evidence triggered a higher-difficulty production probe.",
        )

    @staticmethod
    def _complete(reason: str) -> AdaptiveDecision:
        return AdaptiveDecision(
            action=AdaptiveAction.COMPLETE,
            reason=reason,
            evidence_sufficient=True,
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
        *,
        personalization_context: str | None = None,
        is_follow_up: bool = False,
        parent_question_id=None,
        adaptation_reason: str = "Initial capability probe",
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
            personalization_context=personalization_context,
            is_follow_up=is_follow_up,
            parent_question_id=parent_question_id,
            adaptation_reason=adaptation_reason,
        )
