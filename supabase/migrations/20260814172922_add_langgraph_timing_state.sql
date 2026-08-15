alter table public.assessment_questions
  add column if not exists assessment_area text not null default 'role_capability',
  add column if not exists time_limit_seconds smallint not null default 180,
  add column if not exists issued_at timestamptz,
  add column if not exists expires_at timestamptz;

alter table public.assessment_questions
  drop constraint if exists assessment_questions_area_check,
  drop constraint if exists assessment_questions_time_limit_check;

alter table public.assessment_questions
  add constraint assessment_questions_area_check
  check (assessment_area in (
    'introduction',
    'experience',
    'project',
    'role_capability',
    'professional_judgment'
  )),
  add constraint assessment_questions_time_limit_check
  check (time_limit_seconds in (120, 180, 300));

alter table public.assessment_responses
  add column if not exists submission_reason text not null default 'manual',
  add column if not exists time_spent_seconds smallint;

alter table public.assessment_responses
  drop constraint if exists assessment_responses_submission_reason_check,
  drop constraint if exists assessment_responses_time_spent_check;

alter table public.assessment_responses
  add constraint assessment_responses_submission_reason_check
  check (submission_reason in ('manual', 'time_expired')),
  add constraint assessment_responses_time_spent_check
  check (time_spent_seconds is null or time_spent_seconds between 0 and 1800);
