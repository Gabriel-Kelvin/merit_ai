from __future__ import annotations

import json
import logging
from typing import Protocol

from google import genai
from google.genai import types

from app.assessment.models import CandidateContext, Question, ResponseEvaluation
from app.assessment.rubric import RUBRICS

logger = logging.getLogger(__name__)


class Evaluator(Protocol):
    model_name: str

    def evaluate(
        self, candidate: CandidateContext, question: Question, response_text: str
    ) -> ResponseEvaluation: ...


class GeminiEvaluator:
    def __init__(self, api_key: str, model_name: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.model_name = model_name
        self._client = genai.Client(api_key=api_key)

    def evaluate(
        self, candidate: CandidateContext, question: Question, response_text: str
    ) -> ResponseEvaluation:
        rubric = RUBRICS[question.dimension]
        prompt = f"""
You are the evidence evaluator for Merit AI, a professional engineering readiness assessment.

Evaluate only the evidence present in the candidate's answer. Do not reward buzzwords, inferred
experience, verbosity, or writing style unless communication is the assessed dimension. Be fair to
freshers while maintaining professional standards. A high score requires specific mechanisms,
trade-offs, failure awareness, and verification appropriate to the question.

Candidate context:
{json.dumps(candidate.model_dump(mode="json"), indent=2)}

Assessed dimension: {question.dimension.value}
Dimension purpose: {rubric.purpose}
Strong signals: {list(rubric.strong_signals)}
Weak signals: {list(rubric.weak_signals)}
Question: {question.prompt}
Question intent: {question.intent}
Expected evidence signals: {question.expected_signals}

Candidate answer:
{response_text}

Return a calibrated evaluation. Set follow_up_required when important evidence remains ambiguous or
missing and one focused follow-up could materially change the assessment. Evidence support must be a
short paraphrase, never an invented quote. The reasoning_summary is a concise assessor explanation,
not hidden chain-of-thought.
""".strip()
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.15,
                response_mime_type="application/json",
                response_schema=ResponseEvaluation,
            ),
        )
        if isinstance(response.parsed, ResponseEvaluation):
            return response.parsed
        if not response.text:
            raise RuntimeError("Gemini returned an empty evaluation")
        return ResponseEvaluation.model_validate_json(response.text)


class DeterministicEvaluator:
    """Predictable evaluator used by tests and as an explicit offline demo mode."""

    model_name = "deterministic-test-evaluator"

    def evaluate(
        self, candidate: CandidateContext, question: Question, response_text: str
    ) -> ResponseEvaluation:
        del candidate
        lowered = response_text.lower()
        signals = [signal for signal in question.expected_signals if signal.split()[0] in lowered]
        specificity = min(25, len(response_text.split()) // 4)
        score = min(92, 35 + specificity + len(signals) * 10)
        missing = [signal for signal in question.expected_signals if signal not in signals]
        evidence = [
            {
                "claim": f"Shows awareness of {signal}",
                "support": f"The answer addresses {signal} with some detail.",
                "strength": "moderate",
            }
            for signal in signals[:3]
        ]
        return ResponseEvaluation(
            score=score,
            confidence=0.82 if len(response_text.split()) >= 25 else 0.62,
            evidence=evidence,
            strengths=[f"Addresses {signal}" for signal in signals[:3]],
            gaps=[f"Needs clearer evidence of {signal}" for signal in missing[:3]],
            follow_up_required=score < 70,
            follow_up_focus=missing[0] if missing else None,
            reasoning_summary=(
                "The answer contains relevant engineering evidence, but depth and verification "
                "determine whether a follow-up is required."
            ),
        )
