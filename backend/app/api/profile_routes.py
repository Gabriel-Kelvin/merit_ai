from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth import require_user
from app.profiles import CandidateProfileDraft, SavedCandidateProfile

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("", response_model=SavedCandidateProfile, summary="Read the saved candidate profile")
def get_profile(
    request: Request,
    account_id: Annotated[str, Depends(require_user)],
) -> SavedCandidateProfile:
    profile = request.app.state.profile_store.get(account_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No saved candidate profile exists yet.",
        )
    return profile


@router.put("", response_model=SavedCandidateProfile, summary="Save the candidate profile")
def save_profile(
    draft: CandidateProfileDraft,
    request: Request,
    account_id: Annotated[str, Depends(require_user)],
) -> SavedCandidateProfile:
    existing = request.app.state.profile_store.get(account_id)
    preserved = {}
    for field in ("active_assessment_id", "active_question_remaining_seconds"):
        if field not in draft.model_fields_set and existing is not None:
            preserved[field] = getattr(existing, field)
    if preserved:
        draft = draft.model_copy(update=preserved)
    return request.app.state.profile_store.save(account_id, draft)
