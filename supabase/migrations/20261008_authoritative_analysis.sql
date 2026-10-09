-- Additive recovery migration; preserves existing rows as legacy/unassessed.
-- Apply only to the explicitly configured isolated test project first.
-- Not executed against any real project in this session.
begin;
alter table public.screenings
  add column if not exists analysis_result jsonb;
-- Unavailable model output is SQL NULL, not the string "None" or a fake label.
alter table public.screenings alter column condition_label drop not null;
-- Match the API's hard supported maximum; its effective configured limit is
-- validated before inference/save. Never truncate a disclosure to make it fit.
alter table public.screenings drop constraint if exists screenings_text_length;
alter table public.screenings add constraint screenings_text_length
  check (char_length(text) between 1 and 100000);
-- Make required privileged operation grants explicit; application owner
-- scoping remains mandatory because service_role can bypass RLS.
grant select on public.profiles to service_role;
grant select, insert, delete on public.screenings to service_role;
comment on column public.screenings.analysis_result is
  'Versioned validated AnalysisResult: authoritative safety, raw model values, availability and versions. NULL marks legacy/unassessed.';
commit;
