-- Fase 2: lowongan hasil ekstraksi LLM (PRD 7.2) dan log pemakaian LLM (PRD 7.10).

-- Satu baris per lowongan yang ditempel pengguna. Kolom terstruktur boleh dikoreksi
-- pengguna; `extracted` menyimpan keluaran asli pipeline supaya tingkat koreksi
-- bisa diukur dan hasil analisis bisa direproduksi.
create table if not exists public.job_postings (
  id                    uuid primary key default gen_random_uuid(),
  user_id               uuid not null default auth.uid() references auth.users (id) on delete cascade,
  source_text           text not null check (length(source_text) between 1 and 20000),
  -- sha256 dari teks yang dinormalisasi; cache agar lowongan yang sama tidak
  -- diekstrak ulang (PRD 7.10).
  text_hash             text not null check (text_hash ~ '^[0-9a-f]{64}$'),
  source_url            text check (length(source_url) <= 2000),
  position              text check (length(position) <= 200),
  company               text check (length(company) <= 200),
  location              text check (length(location) <= 200),
  required_skills       text[] not null default '{}' check (cardinality(required_skills) <= 60),
  preferred_skills      text[] not null default '{}' check (cardinality(preferred_skills) <= 60),
  education_level       text check (education_level in ('sma', 'd3', 'd4', 's1', 's2', 's3')),
  education_fields      text[] not null default '{}' check (cardinality(education_fields) <= 30),
  min_experience_years  numeric(4, 1) check (min_experience_years between 0 and 50),
  responsibilities      text[] not null default '{}' check (cardinality(responsibilities) <= 40),
  extracted             jsonb,
  llm_model             text,
  prompt_version        text,
  corrected_at          timestamptz,
  created_at            timestamptz not null default now(),
  updated_at            timestamptz not null default now(),
  unique (user_id, text_hash),
  unique (id, user_id)
);

create index if not exists job_postings_user_created_idx
  on public.job_postings (user_id, created_at desc);

alter table public.job_postings enable row level security;

drop policy if exists "job_postings_own" on public.job_postings;
create policy "job_postings_own" on public.job_postings
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

revoke all on public.job_postings from anon, authenticated;
grant select, insert, update, delete on public.job_postings to authenticated;

drop trigger if exists job_postings_set_updated_at on public.job_postings;
create trigger job_postings_set_updated_at
  before update on public.job_postings
  for each row execute function public.set_updated_at();

-- Lamaran bisa ditautkan ke lowongan asalnya (PRD 7.5). Composite FK menjamin
-- lowongan milik pengguna yang sama; menghapus lowongan hanya melepas tautannya.
alter table public.applications
  add column if not exists job_posting_id uuid;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'applications_job_posting_fkey'
  ) then
    alter table public.applications
      add constraint applications_job_posting_fkey
      foreign key (job_posting_id, user_id)
      references public.job_postings (id, user_id)
      on delete set null (job_posting_id);
  end if;
end;
$$;

create index if not exists applications_job_posting_idx
  on public.applications (job_posting_id) where job_posting_id is not null;

-- Log setiap panggilan LLM: dasar batas harian per pengguna (baris tidak bisa
-- diubah atau dihapus pengguna, jadi menghapus lowongan tidak mengembalikan kuota)
-- dan statistik agregat panel admin di Fase 6.
create table if not exists public.llm_usage (
  id              bigint generated always as identity primary key,
  user_id         uuid not null default auth.uid() references auth.users (id) on delete cascade,
  kind            text not null check (kind in ('job_extract', 'explain')),
  status          text not null check (status in ('ok', 'failed')),
  llm_model       text,
  prompt_version  text,
  latency_ms      integer check (latency_ms >= 0),
  error           text check (length(error) <= 500),
  created_at      timestamptz not null default now()
);

create index if not exists llm_usage_user_kind_created_idx
  on public.llm_usage (user_id, kind, created_at);

alter table public.llm_usage enable row level security;

drop policy if exists "llm_usage_select_own" on public.llm_usage;
create policy "llm_usage_select_own" on public.llm_usage
  for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "llm_usage_insert_own" on public.llm_usage;
create policy "llm_usage_insert_own" on public.llm_usage
  for insert to authenticated
  with check ((select auth.uid()) = user_id);

revoke all on public.llm_usage from anon, authenticated;
grant select, insert on public.llm_usage to authenticated;
