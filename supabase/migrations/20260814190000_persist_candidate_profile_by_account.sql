create table if not exists public.candidate_profiles (
  account_id text primary key,
  profile_json jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint candidate_profiles_account_id_length
    check (char_length(account_id) between 1 and 100),
  constraint candidate_profiles_json_object
    check (jsonb_typeof(profile_json) = 'object')
);

alter table public.candidate_profiles enable row level security;
revoke all on table public.candidate_profiles from anon, authenticated;
grant select, insert, update, delete on table public.candidate_profiles to service_role;

comment on table public.candidate_profiles is
  'Server-managed saved candidate profile and resume context keyed to the Merit application account.';
