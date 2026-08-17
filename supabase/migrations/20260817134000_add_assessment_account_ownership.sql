alter table public.assessments
  add column if not exists account_id text;

create index if not exists assessments_account_id_updated_at_idx
  on public.assessments (account_id, updated_at desc);

comment on column public.assessments.account_id is
  'Server-authenticated Merit account that owns this assessment. Null only for legacy demo rows.';
