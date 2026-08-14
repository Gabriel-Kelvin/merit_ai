from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from supabase import Client, create_client

from app.assessment.models import (
    AssessmentResult,
    AssessmentSession,
    AssessmentStatus,
    CandidateContext,
    DimensionScore,
    EvaluationRecord,
    Question,
    ResponseEvaluation,
)


class SupabaseAssessmentRepository:
    """Server-only persistence adapter. The secret key must never reach the frontend."""

    def __init__(self, url: str, secret_key: str) -> None:
        if not url or not secret_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SECRET_KEY are required")
        self.client: Client = create_client(url, secret_key)

    def create(self, session: AssessmentSession) -> None:
        candidate = session.candidate
        candidate_row = (
            self.client.table("candidates")
            .insert(
                {
                    "public_id": str(uuid4()),
                    "name": candidate.name,
                    "email": candidate.email,
                    "education": candidate.education,
                    "graduation_year": candidate.graduation_year,
                    "experience_level": candidate.experience_level,
                    "target_role": candidate.target_role,
                    "technical_skills": candidate.technical_skills,
                    "projects": [item.model_dump(mode="json") for item in candidate.projects],
                    "ai_tools_used": candidate.ai_tools_used,
                    "professional_links": {
                        "github_url": str(candidate.github_url) if candidate.github_url else None,
                        "linkedin_url": str(candidate.linkedin_url)
                        if candidate.linkedin_url
                        else None,
                    },
                    "context_json": candidate.model_dump(mode="json"),
                }
            )
            .execute()
            .data[0]
        )
        assessment_row = (
            self.client.table("assessments")
            .insert(
                {
                    "public_id": str(session.id),
                    "candidate_id": candidate_row["id"],
                    "status": session.status.value,
                    "current_dimension": session.current_question.dimension.value,
                    "progress": session.progress,
                    "question_count": len(session.questions),
                    "max_questions": session.max_questions,
                    "state_json": self._state_json(session),
                }
            )
            .execute()
            .data[0]
        )
        for question in session.questions:
            self._insert_question(assessment_row["id"], question)

    def get(self, assessment_id: UUID) -> AssessmentSession | None:
        rows = (
            self.client.table("assessments")
            .select("*")
            .eq("public_id", str(assessment_id))
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            return None
        assessment = rows[0]
        candidate_row = (
            self.client.table("candidates")
            .select("context_json")
            .eq("id", assessment["candidate_id"])
            .single()
            .execute()
            .data
        )
        question_rows = (
            self.client.table("assessment_questions")
            .select("*")
            .eq("assessment_id", assessment["id"])
            .order("sequence_no")
            .execute()
            .data
        )
        questions = [self._question_from_row(row) for row in question_rows]
        questions_by_internal_id = {
            row["id"]: question for row, question in zip(question_rows, questions, strict=True)
        }
        response_rows = (
            self.client.table("assessment_responses")
            .select("*")
            .eq("assessment_id", assessment["id"])
            .order("submitted_at")
            .execute()
            .data
        )
        records = [
            EvaluationRecord(
                question=questions_by_internal_id[row["question_id"]],
                response_text=row["response_text"],
                evaluation=ResponseEvaluation.model_validate(row["evaluation_json"]),
            )
            for row in response_rows
        ]
        state = assessment.get("state_json") or {}
        current_id = state.get("current_question_id")
        current = next((question for question in questions if str(question.id) == current_id), None)
        result = self._load_result(assessment["id"], assessment_id)
        return AssessmentSession(
            id=assessment_id,
            candidate=CandidateContext.model_validate(candidate_row["context_json"]),
            status=AssessmentStatus(assessment["status"]),
            current_question=current,
            records=records,
            questions=questions,
            followups_used=state.get("followups_used", {}),
            max_questions=assessment["max_questions"],
            result=result,
        )

    def add_question(self, assessment_id: UUID, question: Question) -> None:
        internal_id = self._assessment_internal_id(assessment_id)
        self._insert_question(internal_id, question)

    def add_response(self, assessment_id: UUID, record: EvaluationRecord) -> None:
        internal_id = self._assessment_internal_id(assessment_id)
        question_row = (
            self.client.table("assessment_questions")
            .select("id")
            .eq("assessment_id", internal_id)
            .eq("public_id", str(record.question.id))
            .single()
            .execute()
            .data
        )
        evaluation = record.evaluation
        self.client.table("assessment_responses").insert(
            {
                "assessment_id": internal_id,
                "question_id": question_row["id"],
                "response_text": record.response_text,
                "evaluation_json": evaluation.model_dump(mode="json"),
                "score": evaluation.score,
                "confidence": evaluation.confidence,
                "evidence_json": [item.model_dump(mode="json") for item in evaluation.evidence],
            }
        ).execute()

    def update(self, session: AssessmentSession) -> None:
        internal_id = self._assessment_internal_id(session.id)
        payload = {
            "status": session.status.value,
            "current_dimension": (
                session.current_question.dimension.value
                if session.current_question
                else "communication"
            ),
            "progress": session.progress,
            "question_count": len(session.questions),
            "state_json": self._state_json(session),
            "updated_at": datetime.now(UTC).isoformat(),
            "completed_at": (
                datetime.now(UTC).isoformat()
                if session.status == AssessmentStatus.COMPLETED
                else None
            ),
        }
        self.client.table("assessments").update(payload).eq("id", internal_id).execute()
        if session.result:
            self._save_result(internal_id, session.result)

    def _assessment_internal_id(self, assessment_id: UUID) -> int:
        row = (
            self.client.table("assessments")
            .select("id")
            .eq("public_id", str(assessment_id))
            .single()
            .execute()
            .data
        )
        return row["id"]

    def _insert_question(self, assessment_id: int, question: Question) -> None:
        self.client.table("assessment_questions").insert(
            {
                "public_id": str(question.id),
                "assessment_id": assessment_id,
                "sequence_no": question.sequence_no,
                "dimension": question.dimension.value,
                "question_type": question.type.value,
                "difficulty": question.difficulty.value,
                "prompt": question.prompt,
                "intent": question.intent,
                "expected_signals": question.expected_signals,
                "personalization_context": question.personalization_context,
                "is_follow_up": question.is_follow_up,
                "parent_question_public_id": (
                    str(question.parent_question_id) if question.parent_question_id else None
                ),
                "adaptation_reason": question.adaptation_reason,
            }
        ).execute()

    @staticmethod
    def _question_from_row(row: dict) -> Question:
        return Question(
            id=row["public_id"],
            sequence_no=row["sequence_no"],
            dimension=row["dimension"],
            type=row["question_type"],
            difficulty=row["difficulty"],
            prompt=row["prompt"],
            intent=row["intent"],
            expected_signals=row["expected_signals"],
            personalization_context=row.get("personalization_context"),
            is_follow_up=row.get("is_follow_up", False),
            parent_question_id=row.get("parent_question_public_id"),
            adaptation_reason=row.get("adaptation_reason") or "Initial capability probe",
        )

    @staticmethod
    def _state_json(session: AssessmentSession) -> dict:
        return {
            "followups_used": session.followups_used,
            "current_question_id": (
                str(session.current_question.id) if session.current_question else None
            ),
        }

    def _save_result(self, assessment_id: int, result: AssessmentResult) -> None:
        self.client.table("assessment_dimension_scores").upsert(
            [
                {
                    "assessment_id": assessment_id,
                    "dimension": item.dimension.value,
                    "score": item.score,
                    "confidence": item.confidence,
                    "evidence_count": item.evidence_count,
                    "strengths": item.strengths,
                    "gaps": item.gaps,
                }
                for item in result.dimensions
            ],
            on_conflict="assessment_id,dimension",
        ).execute()
        self.client.table("assessment_results").upsert(
            {
                "assessment_id": assessment_id,
                "overall_score": result.readiness_score,
                "classification": result.classification.value,
                "summary": result.summary,
                "strengths": result.strengths,
                "gaps": result.gaps,
                "recommendation": result.recommendation.model_dump(mode="json"),
                "evidence_summary": [
                    item.model_dump(mode="json") for item in result.evidence_summary
                ],
                "model": result.model,
                "prompt_version": result.prompt_version,
                "rubric_version": result.rubric_version,
                "result_json": result.model_dump(mode="json"),
            },
            on_conflict="assessment_id",
        ).execute()

    def _load_result(self, internal_id: int, public_id: UUID) -> AssessmentResult | None:
        rows = (
            self.client.table("assessment_results")
            .select("*")
            .eq("assessment_id", internal_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            return None
        row = rows[0]
        if row.get("result_json"):
            return AssessmentResult.model_validate(row["result_json"])
        dimensions = (
            self.client.table("assessment_dimension_scores")
            .select("*")
            .eq("assessment_id", internal_id)
            .execute()
            .data
        )
        recommendation = dict(row["recommendation"])
        priorities = recommendation.get("priority_capabilities") or ["Engineering Fundamentals"]
        recommendation.setdefault("top_development_priority", priorities[0])
        recommendation.setdefault("why", recommendation.get("rationale", "Evidence was limited."))
        recommendation["proof_of_improvement_challenge"] = None
        return AssessmentResult(
            assessment_id=public_id,
            readiness_score=row["overall_score"],
            classification=row["classification"],
            dimensions=[DimensionScore.model_validate(item) for item in dimensions],
            strengths=row["strengths"],
            gaps=row["gaps"],
            evidence_summary=row["evidence_summary"],
            summary=row["summary"],
            recommendation=recommendation,
            model=row["model"],
            prompt_version=row["prompt_version"],
            rubric_version=row["rubric_version"],
        )
