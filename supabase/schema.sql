-- =====================================================================
-- MENTAL.AI - Supabase schema
-- =====================================================================
--
-- Apply with either:
--   supabase db push                       (Supabase CLI, from the repo root)
--   psql "$SUPABASE_DB_URL" -f supabase/schema.sql
--   or paste into Dashboard -> SQL Editor -> New query -> Run
--
-- Idempotent: safe to re-run. Every object is created IF NOT EXISTS and every
-- policy is dropped before it is created.
--
-- DERIVED FROM THE CODE, NOT FROM A TEMPLATE
-- ------------------------------------------
-- The service persists exactly two things:
--
--   auth.users   Supabase Auth owns identity and passwords. This schema never
--                creates a second credential store.
--   profiles     The stable relational anchor for an account: display name and
--                ownership target. Created automatically on signup.
--   screenings   One row per POST /predict. That endpoint is the only writer,
--                and its request/response models are the source of the columns:
--                PredictRequest.text, PredictResponse.primary.*, .urgency.*,
--                .cleaned_text, .lemmatized_text, .provenance_caveat.
--
-- There is no `responses`, `results` or `assessments` table: the application
-- submits one text document and receives one result in a single call, so
-- splitting them would invent an entity the code never creates.
--
-- SENSITIVE DATA NOTE - READ BEFORE APPLYING
-- ------------------------------------------
-- `screenings.text` stores the participant's own words, which for this product
-- is mental-health disclosure. It is protected by RLS and reachable only by the
-- owning account, but it is still health-adjacent data sitting in a cloud
-- database. If you would rather not retain it, drop the two columns below:
--
--   alter table public.screenings drop column text;
--   alter table public.screenings drop column cleaned_text;
--   alter table public.screenings drop column lemmatized_text;
--
-- and remove the three matching keys from ROW_MAPPING in api/db.py. Nothing
-- else in the service depends on them.

-- ---------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------
-- gen_random_uuid() is core in Postgres 13+, but pgcrypto is listed so the
-- schema also applies on older Supabase projects.
create extension if not exists pgcrypto with schema extensions;

-- ---------------------------------------------------------------------
-- Shared trigger: keep updated_at honest
-- ---------------------------------------------------------------------
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------
-- profiles
-- ---------------------------------------------------------------------
-- One row per account, created from auth.users. `id` is the Supabase Auth user
-- id, so every policy below can be expressed as auth.uid() = id.
create table if not exists public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  email        text,
  display_name text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

comment on table public.profiles is
  'Stable per-account record. Identity and password stay in auth.users.';

create index if not exists profiles_display_name_idx
  on public.profiles (display_name);

drop trigger if exists profiles_touch_updated_at on public.profiles;
create trigger profiles_touch_updated_at
  before update on public.profiles
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------------
-- Auto-create a profile on signup
-- ---------------------------------------------------------------------
-- Done in the database rather than in FastAPI or the browser so a row can
-- never be missing because a client call was skipped. display_name prefers
-- what the operator supplied at creation time and otherwise derives the same
-- "Firstname Lastname" shape api/auth.py used to derive in Python.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email, display_name)
  values (
    new.id,
    new.email,
    coalesce(
      nullif(new.raw_user_meta_data ->> 'full_name', ''),
      nullif(new.raw_user_meta_data ->> 'name', ''),
      nullif(split_part(coalesce(new.email, ''), '@', 1), '')
    )
  )
  on conflict (id) do update
    set email        = excluded.email,
        display_name = coalesce(public.profiles.display_name, excluded.display_name);

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------
-- screenings
-- ---------------------------------------------------------------------
-- One row per authenticated POST /predict. Column names track the API's
-- request and response models so the mapping in api/db.py is a rename rather
-- than an interpretation.
create table if not exists public.screenings (
  id                     uuid primary key default gen_random_uuid(),

  -- Ownership. Always the verified token subject; never a value taken from the
  -- request body. Cascade is semantically right: the screening has no meaning
  -- without the person who produced it.
  user_id                uuid not null references auth.users (id) on delete cascade,

  -- Correlates a stored row with the request/response the UI already shows.
  request_id             text not null,

  -- What was screened.
  text                   text not null,
  cleaned_text           text,
  lemmatized_text        text,

  -- Primary model: proxy-labelled condition signal.
  condition_label        text,
  condition_probabilities jsonb not null default '{}'::jsonb,

  -- Secondary model: urgency signal and the threshold actually applied.
  urgency_label          text,
  urgency_probability    numeric(6, 5),
  decision_threshold     numeric(6, 5),
  urgency_flagged        boolean not null default false,

  -- Provenance carried through from the inference layer.
  provenance_caveat      text,
  service_version        text,
  model_latency_ms       numeric(10, 2),
  analysis_result        jsonb,

  created_at             timestamptz not null default now(),
  updated_at             timestamptz not null default now(),

  -- API validates its effective configured cap (1000..100000). This hard upper
  -- bound accommodates all permitted configurations without truncation.
  constraint screenings_text_length check (char_length(text) between 1 and 100000),
  constraint screenings_probability_range check (
    urgency_probability is null or (urgency_probability >= 0 and urgency_probability <= 1)
  )
);

comment on table public.screenings is
  'One row per screening submission. Contains mental-health disclosure; RLS-scoped to the owning account.';

-- The only read pattern is "this account''s history, newest first".
create index if not exists screenings_user_created_idx
  on public.screenings (user_id, created_at desc);

-- Flagged rows are the ones a reviewer would surface; partial because they are
-- a small fraction of the table.
create index if not exists screenings_user_flagged_idx
  on public.screenings (user_id, created_at desc)
  where urgency_flagged;

drop trigger if exists screenings_touch_updated_at on public.screenings;
create trigger screenings_touch_updated_at
  before update on public.screenings
  for each row execute function public.touch_updated_at();

-- ---------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------
-- The service talks to Postgres with the secret key, which bypasses RLS on
-- purpose: FastAPI is the authorisation boundary and derives user_id from a
-- verified token. RLS is the second lock, and the one that matters if anyone
-- ever reaches PostgREST directly with the publishable key. Both are needed:
-- RLS alone does not help if a privileged client writes the wrong user_id, and
-- FastAPI alone does not help if a key leaks.
--
-- No policy anywhere grants access to anon or to another account.

alter table public.profiles   enable row level security;
alter table public.screenings enable row level security;

-- profiles -----------------------------------------------------------------
drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own on public.profiles
  for select to authenticated
  using (auth.uid() = id);

drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own on public.profiles
  for insert to authenticated
  with check (auth.uid() = id);

-- Update only. The owner may correct their own display name; the row cannot be
-- re-pointed at another account because `id` is the auth uid and `with check`
-- re-asserts it.
drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own on public.profiles
  for update to authenticated
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- No delete policy: accounts are removed through Supabase Auth, which cascades.

-- screenings ---------------------------------------------------------------
drop policy if exists screenings_select_own on public.screenings;
create policy screenings_select_own on public.screenings
  for select to authenticated
  using (auth.uid() = user_id);

drop policy if exists screenings_insert_own on public.screenings;
create policy screenings_insert_own on public.screenings
  for insert to authenticated
  with check (auth.uid() = user_id);

drop policy if exists screenings_delete_own on public.screenings;
create policy screenings_delete_own on public.screenings
  for delete to authenticated
  using (auth.uid() = user_id);

-- Deliberately no UPDATE policy: a screening is an immutable record of what was
-- said and what the model returned. Corrections happen by deleting and re-running.

-- ---------------------------------------------------------------------
-- Grants
-- ---------------------------------------------------------------------
-- Revoke the anon role outright so a leaked publishable key cannot read the
-- tables at all, even if a policy were ever dropped by mistake. The `authenticated`
-- grants are what the policies above apply to; the service_role key bypasses RLS
-- through its own grant and is unaffected.
revoke all on public.profiles   from anon;
revoke all on public.screenings from anon;

grant select, insert, update on public.profiles   to authenticated;
grant select, insert, delete on public.screenings to authenticated;
grant select on public.profiles to service_role;
grant select, insert, delete on public.screenings to service_role;

alter table public.profiles   enable row level security;
alter table public.screenings enable row level security;

-- ---------------------------------------------------------------------
-- Verification (read-only, safe to run)
-- ---------------------------------------------------------------------
-- Expect three rows and a non-zero rls count.
--
--   select tablename, rowsecurity from pg_tables
--    where schemaname = 'public' and tablename in ('profiles','screenings');
--
--   select count(*) from pg_policies
--    where schemaname = 'public' and tablename in ('profiles','screenings');
--
-- With SUPABASE_ANON_KEY set, this must return 0 rows:
--
--   curl -s "$SUPABASE_URL/rest/v1/screenings?select=id" \
--        -H "apikey: $SUPABASE_ANON_KEY"
