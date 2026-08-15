from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.assessment.evaluator import (
    DeterministicEvaluator,
    EvaluationUnavailableError,
    Evaluator,
)
from app.assessment.models import (
    AdaptiveAction,
    AdaptiveDecision,
    AssessmentArea,
    AssessmentBlueprint,
    AssessmentMemory,
    AssessmentSession,
    CandidateIntent,
    CapabilityDimension,
    Difficulty,
    GeneratedQuestion,
    Question,
    QuestionType,
    ResponseEvaluation,
)


@dataclass
class QuestionStrategy:
    dimension: CapabilityDimension
    area: AssessmentArea
    action: str
    focus: str | None
    is_follow_up: bool
    decision: AdaptiveDecision


class QuestionPlanner:
    """Policy helpers used by the LangGraph assessment controller."""

    sufficiency_confidence = 0.76

    def plan(self, session: AssessmentSession, intelligence: Evaluator) -> None:
        try:
            session.blueprint = intelligence.plan_assessment(session.candidate)
        except EvaluationUnavailableError:
            # Starting an assessment should not dead-end when every remote provider is busy.
            # This recovery still derives a role-specific capability map from candidate context;
            # subsequent questions and evidence evaluation continue through the AI cascade.
            session.blueprint = DeterministicEvaluator().plan_assessment(session.candidate)
        session.memory.coverage_targets = self._coverage_targets(session)

    def opening_question(self, session: AssessmentSession) -> Question:
        blueprint = self._ensure_blueprint(session)
        dimension = blueprint.dimensions[0]
        draft = GeneratedQuestion(
            type=QuestionType.TEXT,
            difficulty=Difficulty.FOUNDATION,
            prompt=(
                "Tell me about yourself—your background, the experiences that shaped you, "
                "and what you want to do next."
            ),
            intent=(
                "Establish the candidate's own narrative before testing resume claims or "
                "role-specific capability evidence."
            ),
            expected_signals=[
                "clear background",
                "relevant experiences",
                "personal contribution",
                "future direction",
            ],
            personalization_context="Universal opening question; no resume claim is assumed true.",
            time_limit_seconds=180,
        )
        return self._question(
            session,
            dimension,
            draft,
            area=AssessmentArea.INTRODUCTION,
            adaptation_reason=(
                "Every assessment begins with the candidate's own story before adaptive probing."
            ),
        )

    def update_memory(
        self, session: AssessmentSession, evaluation: ResponseEvaluation
    ) -> AssessmentMemory:
        memory = session.memory
        memory.area_counts = dict(
            defaultdict(
                int,
                {
                    area.value: sum(
                        record.question.assessment_area == area for record in session.records
                    )
                    for area in AssessmentArea
                },
            )
        )
        if not memory.coverage_targets:
            memory.coverage_targets = self._coverage_targets(session)
        current = session.current_question
        if current and evaluation.candidate_intent == CandidateIntent.CHANGE_TOPIC:
            skipped = evaluation.requested_topic or current.dimension_label
            if skipped not in memory.avoided_topics:
                memory.avoided_topics.append(skipped)
            memory.avoided_topics = memory.avoided_topics[-20:]
        memory.evidence_gaps = list(
            dict.fromkeys([*memory.evidence_gaps, *evaluation.gaps])
        )[-30:]
        summaries = []
        for record in session.records[-12:]:
            answer = " ".join(record.response_text.split())[:260] or "[no answer]"
            summaries.append(
                f"Q{record.question.sequence_no} {record.question.assessment_area.value}/"
                f"{record.question.dimension_label}: {answer} "
                f"(score {record.evaluation.score}, intent {record.evaluation.candidate_intent})"
            )
        memory.conversation_summary = "\n".join(summaries)[-6000:]
        memory.last_transition = "answer_evaluated"
        return memory

    def choose_strategy(
        self, session: AssessmentSession, evaluation: ResponseEvaluation
    ) -> QuestionStrategy | None:
        blueprint = self._ensure_blueprint(session)
        current = session.current_question
        if current is None or len(session.records) >= session.max_questions:
            return None
        if self._ready_to_finish(session):
            return None

        remaining = session.max_questions - len(session.records)
        explicit_switch = evaluation.candidate_intent == CandidateIntent.CHANGE_TOPIC
        unknown = evaluation.candidate_intent == CandidateIntent.UNKNOWN
        followup_key = f"{current.assessment_area.value}:{current.dimension}"
        used = session.followups_used.get(followup_key, 0)
        evidence_sufficient = self._evidence_sufficient(evaluation)
        target_gap = sum(
            max(0, target - session.memory.area_counts.get(area, 0))
            for area, target in session.memory.coverage_targets.items()
        )

        if (
            not explicit_switch
            and not unknown
            and current.assessment_area != AssessmentArea.INTRODUCTION
            and used < 2
            and remaining > max(2, target_gap // 2)
            and (evaluation.follow_up_required or not evidence_sufficient)
        ):
            focus = evaluation.follow_up_focus or (
                evaluation.gaps[0] if evaluation.gaps else current.expected_signals[0]
            )
            session.followups_used[followup_key] = used + 1
            dimension = self._dimension(blueprint, current.dimension)
            return QuestionStrategy(
                dimension=dimension,
                area=current.assessment_area,
                action=f"probe_gap_{current.assessment_area.value}",
                focus=focus,
                is_follow_up=True,
                decision=AdaptiveDecision(
                    action=AdaptiveAction.PROBE_GAP,
                    reason=f"The next question targets unresolved evidence around {focus}.",
                    targeted_signal=focus,
                    evidence_sufficient=False,
                ),
            )

        excluded = {current.assessment_area} if explicit_switch or unknown else set()
        area = (
            AssessmentArea.EXPERIENCE
            if current.assessment_area == AssessmentArea.INTRODUCTION
            and not explicit_switch
            and not unknown
            else self._highest_value_area(session, excluded)
        )
        dimension = self._highest_value_dimension(session, blueprint, current, explicit_switch)
        if explicit_switch:
            adaptive_action = AdaptiveAction.CHANGE_TOPIC
            reason = (
                f"The candidate requested a different topic, so LangGraph redirected to "
                f"{area.value.replace('_', ' ')} without repeating the skipped subject."
            )
        else:
            adaptive_action = AdaptiveAction.ADVANCE
            reason = (
                f"LangGraph selected {area.value.replace('_', ' ')} as the highest-value "
                "remaining evidence area."
            )
        action = (
            f"stretch_{area.value}"
            if evaluation.score >= 82 and evaluation.confidence >= 0.8
            else f"advance_{area.value}"
        )
        return QuestionStrategy(
            dimension=dimension,
            area=area,
            action=action,
            focus=None,
            is_follow_up=False,
            decision=AdaptiveDecision(
                action=adaptive_action,
                reason=reason,
                evidence_sufficient=evidence_sufficient,
            ),
        )

    def generate(
        self,
        session: AssessmentSession,
        intelligence: Evaluator,
        strategy: QuestionStrategy,
    ) -> Question:
        blueprint = self._ensure_blueprint(session)
        history = self.history(session)
        history.append(
            {
                "type": "assessment_controller",
                "requested_area": strategy.area.value,
                "coverage_counts": session.memory.area_counts,
                "coverage_targets": session.memory.coverage_targets,
                "avoided_topics": session.memory.avoided_topics,
                "remaining_evidence_gaps": session.memory.evidence_gaps[-8:],
                "instruction": (
                    "Ask a new, non-repetitive question in the requested area. Base it on all "
                    "prior answers and evidence, not merely the resume."
                ),
            }
        )
        draft = intelligence.generate_question(
            session.candidate,
            blueprint,
            strategy.dimension,
            history,
            strategy.action,
            strategy.focus,
        )
        current = session.current_question
        return self._question(
            session,
            strategy.dimension,
            draft,
            area=strategy.area,
            is_follow_up=strategy.is_follow_up,
            parent_question_id=current.id if current and strategy.is_follow_up else None,
            adaptation_reason=strategy.decision.reason,
        )

    @staticmethod
    def history(session: AssessmentSession) -> list[dict]:
        return [
            {
                "sequence": record.question.sequence_no,
                "assessment_area": record.question.assessment_area.value,
                "capability": record.question.dimension_label,
                "question": record.question.prompt,
                "answer": record.response_text or "[no answer before timer expired]",
                "submission_reason": record.submission_reason.value,
                "score": record.evaluation.score,
                "confidence": record.evaluation.confidence,
                "candidate_intent": record.evaluation.candidate_intent.value,
                "strengths": record.evaluation.strengths,
                "gaps": record.evaluation.gaps,
                "follow_up_focus": record.evaluation.follow_up_focus,
            }
            for record in session.records
        ]

    @classmethod
    def _evidence_sufficient(cls, evaluation: ResponseEvaluation) -> bool:
        credible = sum(item.strength in {"strong", "moderate"} for item in evaluation.evidence)
        return (
            evaluation.confidence >= cls.sufficiency_confidence
            and evaluation.answer_relevance >= 0.7
            and credible >= 2
            and not evaluation.integrity_flags
        )

    @classmethod
    def _dimension_is_sufficient(cls, session: AssessmentSession, dimension_id: str) -> bool:
        records = [
            record for record in session.records if record.question.dimension == dimension_id
        ]
        return bool(records) and any(
            cls._evidence_sufficient(record.evaluation) for record in records
        )

    def _ready_to_finish(self, session: AssessmentSession) -> bool:
        if len(session.records) < min(14, session.max_questions):
            return False
        blueprint = self._ensure_blueprint(session)
        core_coverage = {
            AssessmentArea.EXPERIENCE.value: 3,
            AssessmentArea.PROJECT.value: 2,
            AssessmentArea.ROLE_CAPABILITY.value: 3,
            AssessmentArea.PROFESSIONAL_JUDGMENT.value: 2,
        }
        return all(
            session.memory.area_counts.get(area, 0) >= minimum
            for area, minimum in core_coverage.items()
        ) and all(
            self._dimension_is_sufficient(session, dimension.id)
            for dimension in blueprint.dimensions
        )

    @staticmethod
    def _coverage_targets(session: AssessmentSession) -> dict[str, int]:
        resume = session.candidate.resume_context
        work_count = len(resume.work_experience) if resume else 0
        project_count = len(session.candidate.projects)
        experience_target = 7 if work_count >= 3 else 5
        project_target = 5 if project_count >= 1 else 3
        capability_target = 5
        judgment_target = max(
            2,
            session.max_questions
            - 1
            - experience_target
            - project_target
            - capability_target,
        )
        targets = {
            AssessmentArea.INTRODUCTION.value: 1,
            AssessmentArea.EXPERIENCE.value: experience_target,
            AssessmentArea.PROJECT.value: project_target,
            AssessmentArea.ROLE_CAPABILITY.value: capability_target,
            AssessmentArea.PROFESSIONAL_JUDGMENT.value: judgment_target,
        }
        while sum(targets.values()) > session.max_questions:
            reducible = max(
                (area for area in targets if area != AssessmentArea.INTRODUCTION.value),
                key=targets.get,
            )
            targets[reducible] -= 1
        return targets

    @staticmethod
    def _highest_value_area(
        session: AssessmentSession, excluded: set[AssessmentArea]
    ) -> AssessmentArea:
        candidates = [area for area in AssessmentArea if area not in excluded]
        candidates = [area for area in candidates if area != AssessmentArea.INTRODUCTION]
        return max(
            candidates,
            key=lambda area: (
                session.memory.coverage_targets.get(area.value, 0)
                - session.memory.area_counts.get(area.value, 0),
                -session.memory.area_counts.get(area.value, 0),
            ),
        )

    @staticmethod
    def _highest_value_dimension(
        session: AssessmentSession,
        blueprint: AssessmentBlueprint,
        current: Question,
        exclude_current: bool,
    ) -> CapabilityDimension:
        scores: dict[str, list[float]] = defaultdict(list)
        counts: dict[str, int] = defaultdict(int)
        for record in session.records:
            counts[record.question.dimension] += 1
            scores[record.question.dimension].append(
                record.evaluation.score * max(record.evaluation.confidence, 0.2)
            )
        options = [
            item
            for item in blueprint.dimensions
            if not exclude_current or item.id != current.dimension
        ] or blueprint.dimensions
        return min(
            options,
            key=lambda item: (
                counts[item.id],
                sum(scores[item.id]) / len(scores[item.id]) if scores[item.id] else 0,
            ),
        )

    @staticmethod
    def _dimension(blueprint: AssessmentBlueprint, dimension_id: str) -> CapabilityDimension:
        return next(item for item in blueprint.dimensions if item.id == dimension_id)

    @staticmethod
    def _ensure_blueprint(session: AssessmentSession) -> AssessmentBlueprint:
        if session.blueprint:
            return session.blueprint
        ids = list(dict.fromkeys(question.dimension for question in session.questions)) or [
            "role_capability"
        ]
        weight = 1 / len(ids)
        session.blueprint = AssessmentBlueprint(
            role_family=session.candidate.target_role,
            rationale="Recovered assessment capability state.",
            dimensions=[
                CapabilityDimension(
                    id=dimension_id,
                    label=dimension_id.replace("_", " ").title(),
                    purpose="Assess evidence for this recovered role capability.",
                    strong_signals=["specific knowledge", "applied example", "verification"],
                    weak_signals=["vague claims"],
                    weight=weight,
                )
                for dimension_id in ids
            ],
        )
        return session.blueprint

    @staticmethod
    def complete(reason: str) -> AdaptiveDecision:
        return AdaptiveDecision(
            action=AdaptiveAction.COMPLETE,
            reason=reason,
            evidence_sufficient=True,
        )

    @staticmethod
    def _question(
        session: AssessmentSession,
        dimension: CapabilityDimension,
        draft: GeneratedQuestion,
        *,
        area: AssessmentArea,
        is_follow_up: bool = False,
        parent_question_id=None,
        adaptation_reason: str,
    ) -> Question:
        issued_at = datetime.now(UTC)
        return Question(
            id=uuid4(),
            sequence_no=len(session.questions) + 1,
            dimension=dimension.id,
            dimension_label=dimension.label,
            type=draft.type,
            difficulty=draft.difficulty,
            prompt=concise_prompt(draft.prompt),
            intent=draft.intent,
            expected_signals=draft.expected_signals,
            personalization_context=draft.personalization_context,
            is_follow_up=is_follow_up,
            parent_question_id=parent_question_id,
            adaptation_reason=adaptation_reason,
            assessment_area=area,
            time_limit_seconds=draft.time_limit_seconds,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=draft.time_limit_seconds),
        )


def concise_prompt(prompt: str, max_words: int = 38) -> str:
    """Keep generated questions readable without losing their personalized setup."""
    normalized = re.sub(r"\s+", " ", prompt).strip()
    words = normalized.split()
    if len(words) <= max_words:
        return normalized
    context = " ".join(words[:18]).rstrip(".,;:!?-")
    return f"{context}... What would you do next, why, and how would you verify the result?"
