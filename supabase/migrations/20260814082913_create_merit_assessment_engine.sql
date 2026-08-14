create extension if not exists pgcrypto;

create table public.candidates (
  id bigint generated always as identity primary key,
  public_id uuid not null default gen_random_uuid() unique,
  auth_user_id uuid unique references auth.users(id) on delete cascade,
  name text not null,
  email text,
  education text,
  graduation_year smallint,
  experience_level text not null,
  target_role text not null,
  technical_skills text[] not null default '{}',
  projects jsonb not null default '[]'::jsonb,
  ai_tools_used text[] not null default '{}',
  professional_links jsonb not null default '{}'::jsonb,
  context_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint candidates_graduation_year_check
    check (graduation_year is null or graduation_year between 1950 and 2100),
  constraint candidates_projects_array_check check (jsonb_typeof(projects) = 'array'),
  constraint candidates_links_object_check check (jsonb_typeof(professional_links) = 'object'),
  constraint candidates_context_object_check check (jsonb_typeof(context_json) = 'object')
);

create table public.assessments (
  id bigint generated always as identity primary key,
  public_id uuid not null default gen_random_uuid() unique,
  candidate_id bigint not null references public.candidates(id) on delete cascade,
  assessment_version text not null default 'merit-v1',
  status text not null default 'in_progress',
  current_dimension text not null default 'engineering_fundamentals',
  progress smallint not null default 0,
  question_count smallint not null default 0,
  max_questions smallint not null default 8,
  state_json jsonb not null default '{}'::jsonb,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  updated_at timestamptz not null default now(),
  constraint assessments_status_check check (status in ('in_progress', 'completed', 'failed')),
  constraint assessments_progress_check check (progress between 0 and 100),
  constraint assessments_question_count_check check (question_count >= 0),
  constraint assessments_max_questions_check check (max_questions between 3 and 20),
  constraint assessments_state_object_check check (jsonb_typeof(state_json) = 'object')
);

create table public.assessment_questions (
  id bigint generated always as identity primary key,
  public_id uuid not null default gen_random_uuid() unique,
  assessment_id bigint not null references public.assessments(id) on delete cascade,
  sequence_no smallint not null,
  dimension text not null,
  question_type text not null,
  difficulty text not null,
  prompt text not null,
  intent text not null,
  expected_signals jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  constraint assessment_questions_sequence_check check (sequence_no > 0),
  constraint assessment_questions_type_check
    check (question_type in ('text', 'scenario', 'code_review', 'debugging', 'agent_instruction')),
  constraint assessment_questions_difficulty_check
    check (difficulty in ('foundation', 'standard', 'advanced')),
  constraint assessment_questions_signals_array_check check (jsonb_typeof(expected_signals) = 'array'),
  constraint assessment_questions_assessment_sequence_unique unique (assessment_id, sequence_no)
);

create table public.assessment_responses (
  id bigint generated always as identity primary key,
  public_id uuid not null default gen_random_uuid() unique,
  assessment_id bigint not null references public.assessments(id) on delete cascade,
  question_id bigint not null references public.assessment_questions(id) on delete cascade,
  response_text text not null,
  evaluation_json jsonb not null,
  score smallint not null,
  confidence numeric(4,3) not null,
  evidence_json jsonb not null default '[]'::jsonb,
  submitted_at timestamptz not null default now(),
  constraint assessment_responses_score_check check (score between 0 and 100),
  constraint assessment_responses_confidence_check check (confidence between 0 and 1),
  constraint assessment_responses_evaluation_object_check check (jsonb_typeof(evaluation_json) = 'object'),
  constraint assessment_responses_evidence_array_check check (jsonb_typeof(evidence_json) = 'array'),
  constraint assessment_responses_question_unique unique (assessment_id, question_id)
);

create table public.assessment_dimension_scores (
  id bigint generated always as identity primary key,
  assessment_id bigint not null references public.assessments(id) on delete cascade,
  dimension text not null,
  score smallint not null,
  confidence numeric(4,3) not null,
  evidence_count smallint not null default 0,
  strengths jsonb not null default '[]'::jsonb,
  gaps jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  constraint dimension_scores_score_check check (score between 0 and 100),
  constraint dimension_scores_confidence_check check (confidence between 0 and 1),
  constraint dimension_scores_evidence_count_check check (evidence_count >= 0),
  constraint dimension_scores_strengths_array_check check (jsonb_typeof(strengths) = 'array'),
  constraint dimension_scores_gaps_array_check check (jsonb_typeof(gaps) = 'array'),
  constraint dimension_scores_assessment_dimension_unique unique (assessment_id, dimension)
);

create table public.assessment_results (
  id bigint generated always as identity primary key,
  public_id uuid not null default gen_random_uuid() unique,
  assessment_id bigint not null unique references public.assessments(id) on delete cascade,
  overall_score smallint not null,
  classification text not null,
  summary text not null,
  strengths jsonb not null default '[]'::jsonb,
  gaps jsonb not null default '[]'::jsonb,
  recommendation jsonb not null,
  evidence_summary jsonb not null default '[]'::jsonb,
  model text not null,
  prompt_version text not null default 'assessment-v1',
  rubric_version text not null default 'rubric-v1',
  generated_at timestamptz not null default now(),
  constraint assessment_results_score_check check (overall_score between 0 and 100),
  constraint assessment_results_classification_check
    check (classification in ('READY', 'TARGETED_DEVELOPMENT', 'STRUCTURED_DEVELOPMENT', 'FOUNDATION_DEVELOPMENT')),
  constraint assessment_results_strengths_array_check check (jsonb_typeof(strengths) = 'array'),
  constraint assessment_results_gaps_array_check check (jsonb_typeof(gaps) = 'array'),
  constraint assessment_results_recommendation_object_check check (jsonb_typeof(recommendation) = 'object'),
  constraint assessment_results_evidence_array_check check (jsonb_typeof(evidence_summary) = 'array')
);

create index candidates_auth_user_id_idx on public.candidates (auth_user_id)
  where auth_user_id is not null;
create index assessments_candidate_id_started_at_idx
  on public.assessments (candidate_id, started_at desc);
create index assessments_in_progress_idx
  on public.assessments (candidate_id, updated_at desc) where status = 'in_progress';
create index assessment_questions_assessment_id_idx
  on public.assessment_questions (assessment_id);
create index assessment_responses_assessment_id_idx
  on public.assessment_responses (assessment_id);
create index assessment_responses_question_id_idx
  on public.assessment_responses (question_id);
create index assessment_dimension_scores_assessment_id_idx
  on public.assessment_dimension_scores (assessment_id);

alter table public.candidates enable row level security;
alter table public.assessments enable row level security;
alter table public.assessment_questions enable row level security;
alter table public.assessment_responses enable row level security;
alter table public.assessment_dimension_scores enable row level security;
alter table public.assessment_results enable row level security;

revoke all on public.candidates from anon, authenticated;
revoke all on public.assessments from anon, authenticated;
revoke all on public.assessment_questions from anon, authenticated;
revoke all on public.assessment_responses from anon, authenticated;
revoke all on public.assessment_dimension_scores from anon, authenticated;
revoke all on public.assessment_results from anon, authenticated;

grant select, insert, update, delete on public.candidates to service_role;
grant select, insert, update, delete on public.assessments to service_role;
grant select, insert, update, delete on public.assessment_questions to service_role;
grant select, insert, update, delete on public.assessment_responses to service_role;
grant select, insert, update, delete on public.assessment_dimension_scores to service_role;
grant select, insert, update, delete on public.assessment_results to service_role;
grant usage, select on all sequences in schema public to service_role;

comment on table public.assessment_responses is
  'Immutable response evidence and validated AI evaluation used to calculate auditable readiness scores.';
comment on table public.assessment_results is
  'Versioned, evidence-backed final readiness result generated by Merit AI.';
