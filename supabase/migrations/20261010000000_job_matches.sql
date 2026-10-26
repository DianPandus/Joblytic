-- Fase 3: hasil pencocokan profil dengan lowongan (PRD 7.3).

-- Snapshot skor terakhir per lowongan, dihitung deterministik oleh backend
-- (app/matching.py). Disimpan supaya halaman bisa langsung tampil dan skor antar
-- lowongan bisa dibandingkan; dihitung ulang setiap kali halaman lowongan dibuka.
create table if not exists public.job_matches (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null default auth.uid() references auth.users (id) on delete cascade,
  job_posting_id  uuid not null,
  -- null bila lowongan tidak mensyaratkan apa pun yang bisa dinilai.
  score           integer check (score between 0 and 100),
  -- Rincian per kategori, bukti (ID entri/butir profil), dan daftar gap.
  result          jsonb not null,
  weights         jsonb not null,
  scorer_version  text not null,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (job_posting_id),
  foreign key (job_posting_id, user_id)
    references public.job_postings (id, user_id) on delete cascade
);

create index if not exists job_matches_user_idx on public.job_matches (user_id);

alter table public.job_matches enable row level security;

drop policy if exists "job_matches_own" on public.job_matches;
create policy "job_matches_own" on public.job_matches
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

revoke all on public.job_matches from anon, authenticated;
grant select, insert, update, delete on public.job_matches to authenticated;

drop trigger if exists job_matches_set_updated_at on public.job_matches;
create trigger job_matches_set_updated_at
  before update on public.job_matches
  for each row execute function public.set_updated_at();
