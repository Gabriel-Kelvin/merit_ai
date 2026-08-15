from __future__ import annotations

from datetime import UTC, datetime
from threading import RLock
from uuid import UUID

from pydantic import BaseModel, Field
from supabase import Client, create_client

from app.assessment.models import CandidateContext
from app.resumes.models import ResumeProfile


class ProfileFormValues(BaseModel):
    name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=320)
    education: str = Field(default="", max_length=300)
    graduation_year: str = Field(default="", max_length=4)
    experience_level: str = Field(default="", max_length=80)
    target_role: str = Field(default="", max_length=120)
    skills: str = Field(default="", max_length=2000)


class CandidateProfileDraft(BaseModel):
    form_values: ProfileFormValues = Field(default_factory=ProfileFormValues)
    resume_profile: ResumeProfile | None = None
    resume_context_text: str | None = Field(default=None, max_length=12_000)
    resume_name: str | None = Field(default=None, max_length=255)
    candidate: CandidateContext | None = None
    active_assessment_id: UUID | None = None
    active_question_remaining_seconds: int | None = Field(default=None, ge=0, le=300)


class SavedCandidateProfile(CandidateProfileDraft):
    updated_at: datetime


class MemoryCandidateProfileStore:
    def __init__(self) -> None:
        self._profiles: dict[str, SavedCandidateProfile] = {}
        self._lock = RLock()

    def get(self, account_id: str) -> SavedCandidateProfile | None:
        with self._lock:
            return self._profiles.get(account_id)

    def save(self, account_id: str, draft: CandidateProfileDraft) -> SavedCandidateProfile:
        saved = SavedCandidateProfile(
            **draft.model_dump(), updated_at=datetime.now(UTC)
        )
        with self._lock:
            self._profiles[account_id] = saved
        return saved


class SupabaseCandidateProfileStore:
    def __init__(self, url: str, secret_key: str) -> None:
        self.client: Client = create_client(url, secret_key)

    def get(self, account_id: str) -> SavedCandidateProfile | None:
        rows = (
            self.client.table("candidate_profiles")
            .select("profile_json,updated_at")
            .eq("account_id", account_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            return None
        return SavedCandidateProfile(
            **rows[0]["profile_json"], updated_at=rows[0]["updated_at"]
        )

    def save(self, account_id: str, draft: CandidateProfileDraft) -> SavedCandidateProfile:
        row = (
            self.client.table("candidate_profiles")
            .upsert(
                {
                    "account_id": account_id,
                    "profile_json": draft.model_dump(mode="json"),
                    "updated_at": datetime.now(UTC).isoformat(),
                },
                on_conflict="account_id",
            )
            .execute()
            .data[0]
        )
        return SavedCandidateProfile(
            **row["profile_json"], updated_at=row["updated_at"]
        )
