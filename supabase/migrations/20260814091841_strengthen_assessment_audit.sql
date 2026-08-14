alter table public.assessment_questions
  add column if not exists personalization_context text,
  add column if not exists is_follow_up boolean not null default false,
  add column if not exists parent_question_public_id uuid,
  add column if not exists adaptation_reason text not null default 'Initial capability probe';

alter table public.assessment_results
  add column if not exists result_json jsonb;

alter table public.assessment_results
  drop constraint if exists assessment_results_result_object_check;

alter table public.assessment_results
  add constraint assessment_results_result_object_check
  check (result_json is null or jsonb_typeof(result_json) = 'object');
