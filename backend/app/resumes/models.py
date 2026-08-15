from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ResumeProject(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    technologies: list[str] = Field(default_factory=list, max_length=20)


class ResumeWorkExperience(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    company: str | None = Field(default=None, max_length=160)
    start_date: str | None = Field(default=None, max_length=40)
    end_date: str | None = Field(default=None, max_length=40)
    description: str | None = Field(default=None, max_length=1200)
    achievements: list[str] = Field(default_factory=list, max_length=8)
    technologies: list[str] = Field(default_factory=list, max_length=20)


class ResumeProfile(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    education: str | None = Field(default=None, max_length=300)
    graduation_year: int | None = Field(default=None, ge=1950, le=2100)
    experience_level: str | None = Field(default=None, max_length=80)
    target_role: str | None = Field(default=None, max_length=120)
    professional_summary: str | None = Field(default=None, max_length=1200)
    technical_skills: list[str] = Field(default_factory=list, max_length=30)
    projects: list[ResumeProject] = Field(default_factory=list, max_length=3)
    work_experience: list[ResumeWorkExperience] = Field(default_factory=list, max_length=8)
    achievements: list[str] = Field(default_factory=list, max_length=12)
    certifications: list[str] = Field(default_factory=list, max_length=12)
    additional_context: list[str] = Field(default_factory=list, max_length=12)

    @field_validator(
        "name",
        "email",
        "education",
        "experience_level",
        "target_role",
        "professional_summary",
        mode="before",
    )
    @classmethod
    def empty_strings_are_missing(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator(
        "technical_skills",
        "achievements",
        "certifications",
        "additional_context",
    )
    @classmethod
    def normalize_lists(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip() for value in values if value.strip()))


class ResumeParseResponse(BaseModel):
    filename: str
    profile: ResumeProfile
    extracted_fields: list[str]
    warnings: list[str] = Field(default_factory=list)
    parser_model: str
    context_text: str = Field(
        max_length=12_000,
        description=(
            "Readable resume text retained by the client for assessment personalization. "
            "The binary upload is not stored."
        ),
    )
