from __future__ import annotations

from collections import defaultdict

from app.assessment.models import (
    AssessmentResult,
    AssessmentSession,
    DimensionScore,
    ReadinessClassification,
    Recommendation,
)
from app.assessment.rubric import DIMENSION_ORDER, RUBRICS


def build_result(session: AssessmentSession, model_name: str) -> AssessmentResult:
    by_dimension = defaultdict(list)
    for record in session.records:
        by_dimension[record.question.dimension].append(record.evaluation)

    dimension_scores: list[DimensionScore] = []
    for dimension in DIMENSION_ORDER:
        evaluations = by_dimension[dimension]
        if evaluations:
            confidence_total = sum(max(item.confidence, 0.1) for item in evaluations)
            score = round(
                sum(item.score * max(item.confidence, 0.1) for item in evaluations)
                / confidence_total
            )
            confidence = round(sum(item.confidence for item in evaluations) / len(evaluations), 3)
            strengths = _dedupe(
                value for evaluation in evaluations for value in evaluation.strengths
            )[:3]
            gaps = _dedupe(value for evaluation in evaluations for value in evaluation.gaps)[:3]
            evidence_count = sum(len(item.evidence) for item in evaluations)
        else:
            score, confidence, strengths = 0, 0.0, []
            gaps = ["Insufficient evidence collected"]
            evidence_count = 0
        dimension_scores.append(
            DimensionScore(
                dimension=dimension,
                score=score,
                confidence=confidence,
                evidence_count=evidence_count,
                strengths=strengths,
                gaps=gaps,
            )
        )

    overall = round(sum(item.score * RUBRICS[item.dimension].weight for item in dimension_scores))
    classification = classify(overall, dimension_scores)
    strengths = _dedupe(value for item in dimension_scores for value in item.strengths)[:5]
    gaps = _dedupe(
        value
        for item in sorted(dimension_scores, key=lambda item: item.score)
        for value in item.gaps
    )[:5]
    evidence = [
        evidence_item for record in session.records for evidence_item in record.evaluation.evidence
    ][:10]
    recommendation = build_recommendation(classification, dimension_scores, gaps)
    strongest = max(dimension_scores, key=lambda item: item.score)
    weakest = min(dimension_scores, key=lambda item: item.score)
    summary = (
        f"{session.candidate.name} demonstrates the strongest evidence in "
        f"{strongest.dimension.value.replace('_', ' ')} ({strongest.score}/100). "
        f"The highest-value development area is {weakest.dimension.value.replace('_', ' ')} "
        f"({weakest.score}/100). The result is based on {len(evidence)} recorded evidence signals "
        "across the assessment, with confidence retained per response."
    )
    return AssessmentResult(
        assessment_id=session.id,
        readiness_score=overall,
        classification=classification,
        dimensions=dimension_scores,
        strengths=strengths,
        gaps=gaps,
        evidence_summary=evidence,
        summary=summary,
        recommendation=recommendation,
        model=model_name,
    )


def classify(overall: int, dimensions: list[DimensionScore]) -> ReadinessClassification:
    minimum = min(item.score for item in dimensions)
    low_dimensions = sum(item.score < 60 for item in dimensions)
    if overall >= 80 and minimum >= 65:
        return ReadinessClassification.READY
    if overall >= 65 and low_dimensions <= 2:
        return ReadinessClassification.TARGETED_DEVELOPMENT
    if overall >= 45:
        return ReadinessClassification.STRUCTURED_DEVELOPMENT
    return ReadinessClassification.FOUNDATION_DEVELOPMENT


def build_recommendation(
    classification: ReadinessClassification,
    dimensions: list[DimensionScore],
    gaps: list[str],
) -> Recommendation:
    weakest = sorted(dimensions, key=lambda item: item.score)[:2]
    priorities = [item.dimension.value.replace("_", " ").title() for item in weakest]
    titles = {
        ReadinessClassification.READY: "Ready for opportunity matching",
        ReadinessClassification.TARGETED_DEVELOPMENT: "Targeted capability development",
        ReadinessClassification.STRUCTURED_DEVELOPMENT: "Structured AI engineering development",
        ReadinessClassification.FOUNDATION_DEVELOPMENT: "Strengthen engineering foundations",
    }
    actions = [f"Complete one focused project exercise in {priority}." for priority in priorities]
    actions.append("Reassess using a new practical scenario and compare evidence, not only scores.")
    rationale = (
        f"The recommendation focuses on {', '.join(priorities)} because these areas currently "
        "limit the candidate's overall readiness."
    )
    if gaps:
        rationale += f" The most repeated evidence gap was: {gaps[0]}."
    challenge = (
        f"Build or repair a small production workflow that exercises {priorities[0]}, then submit "
        "the implementation, tests, failure cases, and a short verification note."
    )
    return Recommendation(
        pathway=classification,
        title=titles[classification],
        rationale=rationale,
        priority_capabilities=priorities,
        next_actions=actions,
        proof_of_improvement_challenge=challenge,
    )


def _dedupe(values) -> list[str]:
    return list(dict.fromkeys(value.strip() for value in values if value and value.strip()))
