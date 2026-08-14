from __future__ import annotations

from collections import defaultdict

from app.assessment.models import (
    AssessmentResult,
    AssessmentSession,
    Dimension,
    DimensionProgress,
    DimensionScore,
    EvaluationTraceItem,
    ReadinessClassification,
    Recommendation,
    SignalStatus,
)
from app.assessment.rubric import DIMENSION_ORDER, RUBRICS

STRENGTH_VALUES = {"strong": 1.0, "moderate": 0.7, "weak": 0.25, "missing": 0.0}


def build_dimension_progress(session: AssessmentSession) -> list[DimensionProgress]:
    by_dimension = defaultdict(list)
    for record in session.records:
        by_dimension[record.question.dimension].append(record.evaluation)

    progress: list[DimensionProgress] = []
    for dimension in DIMENSION_ORDER:
        evaluations = by_dimension[dimension]
        confidence = (
            sum(item.confidence for item in evaluations) / len(evaluations) if evaluations else 0
        )
        credible = sum(
            evidence.strength in {"strong", "moderate"}
            for evaluation in evaluations
            for evidence in evaluation.evidence
        )
        progress.append(
            DimensionProgress(
                dimension=dimension,
                questions_answered=len(evaluations),
                credible_evidence_count=credible,
                confidence=round(confidence, 3),
                evidence_sufficient=bool(evaluations) and confidence >= 0.76 and credible >= 2,
            )
        )
    return progress


def build_result(session: AssessmentSession, model_name: str) -> AssessmentResult:
    by_dimension = defaultdict(list)
    for record in session.records:
        by_dimension[record.question.dimension].append(record.evaluation)

    dimension_scores = [
        _score_dimension(dimension, by_dimension[dimension]) for dimension in DIMENSION_ORDER
    ]
    overall = round(sum(item.score * RUBRICS[item.dimension].weight for item in dimension_scores))
    overall_confidence = round(
        sum(item.confidence * RUBRICS[item.dimension].weight for item in dimension_scores), 3
    )
    classification = classify(overall, dimension_scores, overall_confidence)
    strengths = _dedupe(value for item in dimension_scores for value in item.strengths)[:5]
    gaps = _dedupe(
        value
        for item in sorted(dimension_scores, key=lambda item: (item.score, item.confidence))
        for value in item.gaps
    )[:5]
    evidence = [
        evidence_item
        for record in session.records
        for evidence_item in record.evaluation.evidence
        if evidence_item.strength != "missing"
    ][:15]
    trace = [
        EvaluationTraceItem(
            question_id=record.question.id,
            sequence_no=record.question.sequence_no,
            dimension=record.question.dimension,
            difficulty=record.question.difficulty,
            question=record.question.prompt,
            score=record.evaluation.score,
            confidence=record.evaluation.confidence,
            reasoning_summary=record.evaluation.reasoning_summary,
            evidence=record.evaluation.evidence,
            strengths=record.evaluation.strengths,
            gaps=record.evaluation.gaps,
            evaluator_model=record.evaluation.evaluator_model,
        )
        for record in session.records
    ]
    recommendation = build_recommendation(classification, dimension_scores, gaps)
    strongest = max(dimension_scores, key=lambda item: (item.score, item.confidence))
    weakest = min(dimension_scores, key=lambda item: (item.score, item.confidence))
    if strongest.score - weakest.score < 5:
        summary = (
            f"{session.candidate.name} demonstrates balanced evidence across the assessed "
            f"capabilities ({weakest.score}-{strongest.score}/100). The conclusion is grounded "
            f"in {len(evidence)} evidence signals with "
            f"{_confidence_label(overall_confidence).lower()} "
            "overall confidence."
        )
    else:
        summary = (
            f"{session.candidate.name}'s strongest demonstrated capability is "
            f"{_label(strongest.dimension)} ({strongest.score}/100). The most limiting capability "
            f"is {_label(weakest.dimension)} ({weakest.score}/100). This conclusion is grounded in "
            f"{len(evidence)} evidence signals with "
            f"{_confidence_label(overall_confidence).lower()} "
            "overall confidence."
        )
    return AssessmentResult(
        assessment_id=session.id,
        readiness_score=overall,
        classification=classification,
        dimensions=dimension_scores,
        strengths=strengths,
        gaps=gaps,
        evidence_summary=evidence,
        evaluation_trace=trace,
        summary=summary,
        recommendation=recommendation,
        overall_confidence=overall_confidence,
        confidence_label=_confidence_label(overall_confidence),
        model=model_name,
    )


def _score_dimension(dimension: Dimension, evaluations) -> DimensionScore:
    if not evaluations:
        return DimensionScore(
            dimension=dimension,
            score=0,
            confidence=0,
            evidence_count=0,
            gaps=["Insufficient evidence collected"],
            limiting_gap="Insufficient evidence collected",
        )

    confidence_total = sum(max(item.confidence, 0.1) for item in evaluations)
    raw_score = sum(
        item.score * max(item.confidence, 0.1) for item in evaluations
    ) / confidence_total
    confidence = sum(item.confidence for item in evaluations) / len(evaluations)
    evidence_items = [item for evaluation in evaluations for item in evaluation.evidence]
    credible_items = [item for item in evidence_items if item.strength in {"strong", "moderate"}]
    evidence_quality = (
        round(
            100
            * sum(STRENGTH_VALUES.get(item.strength, 0) for item in evidence_items)
            / len(evidence_items)
        )
        if evidence_items
        else 0
    )
    demonstrated_signals = {
        signal.signal
        for evaluation in evaluations
        for signal in evaluation.signal_assessments
        if signal.status in {SignalStatus.DEMONSTRATED, SignalStatus.PARTIAL}
    }
    expected_signal_count = len(RUBRICS[dimension].strong_signals)
    coverage = min(1.0, len(demonstrated_signals) / max(expected_signal_count, 1))
    reliability = min(0.95, 0.55 + 0.25 * confidence + 0.2 * coverage)
    score = round(50 + (raw_score - 50) * reliability)
    if len(credible_items) < 2:
        score = min(score, 64)
        confidence = min(confidence, 0.65)

    strengths = _dedupe(value for item in evaluations for value in item.strengths)[:3]
    gaps = _dedupe(value for item in evaluations for value in item.gaps)[:3]
    limiting_gap = gaps[0] if gaps else None
    rationale = (
        f"Score reflects {len(credible_items)} credible evidence signals across "
        f"{len(evaluations)} response{'s' if len(evaluations) != 1 else ''}. "
        f"Evidence quality is {evidence_quality}/100 and confidence is "
        f"{_confidence_label(confidence).lower()}."
    )
    return DimensionScore(
        dimension=dimension,
        score=max(0, min(100, score)),
        confidence=round(confidence, 3),
        evidence_count=len(credible_items),
        strengths=strengths,
        gaps=gaps,
        evidence_quality=evidence_quality,
        confidence_label=_confidence_label(confidence),
        rationale=rationale,
        limiting_gap=limiting_gap,
    )


def classify(
    overall: int, dimensions: list[DimensionScore], overall_confidence: float = 1.0
) -> ReadinessClassification:
    minimum = min(item.score for item in dimensions)
    low_dimensions = sum(item.score < 60 for item in dimensions)
    insufficient_dimensions = sum(item.evidence_count == 0 for item in dimensions)
    ready = (
        overall >= 80
        and minimum >= 65
        and overall_confidence >= 0.72
        and not insufficient_dimensions
    )
    if ready:
        return ReadinessClassification.READY
    if overall >= 65 and low_dimensions <= 2 and insufficient_dimensions <= 1:
        return ReadinessClassification.TARGETED_DEVELOPMENT
    if overall >= 45:
        return ReadinessClassification.STRUCTURED_DEVELOPMENT
    return ReadinessClassification.FOUNDATION_DEVELOPMENT


def build_recommendation(
    classification: ReadinessClassification,
    dimensions: list[DimensionScore],
    gaps: list[str],
) -> Recommendation:
    weakest = sorted(dimensions, key=lambda item: (item.score, item.confidence))[:2]
    priorities = [_label(item.dimension) for item in weakest]
    titles = {
        ReadinessClassification.READY: "Ready with focused growth priorities",
        ReadinessClassification.TARGETED_DEVELOPMENT: "Targeted capability development",
        ReadinessClassification.STRUCTURED_DEVELOPMENT: "Structured AI engineering development",
        ReadinessClassification.FOUNDATION_DEVELOPMENT: "Strengthen engineering foundations",
    }
    limiting_gap = gaps[0] if gaps else "More specific, verifiable evidence is needed."
    actions = [
        f"Study and document the core decision patterns in {priorities[0]}.",
        f"Review two production examples related to {priorities[1]} and compare their trade-offs.",
        "Use a verification checklist when explaining future engineering decisions.",
    ]
    rationale = (
        f"The recommendation prioritizes {priorities[0]} because it has the lowest combination "
        "of demonstrated score, evidence quality, and evaluator confidence."
    )
    return Recommendation(
        pathway=classification,
        title=titles[classification],
        rationale=rationale,
        priority_capabilities=priorities,
        next_actions=actions,
        top_development_priority=priorities[0],
        why=limiting_gap,
        proof_of_improvement_challenge=None,
    )


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.8:
        return "High"
    if confidence >= 0.62:
        return "Moderate"
    return "Low"


def _label(dimension: Dimension) -> str:
    return dimension.value.replace("_", " ").title()


def _dedupe(values) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))
