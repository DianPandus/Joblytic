-- Fase 1: tracker lamaran.
-- Tabel lowongan (hasil ekstraksi) dan entri profil menyusul bersama fiturnya
-- (ekstraksi CV di Fase 1, ekstraksi lowongan di Fase 2), supaya skemanya
-- mengikuti bentuk keluaran ekstraksi yang sebenarnya.

-- Tahap lamaran (PRD 7.5): Disiapkan, Dikirim, Tes/Asesmen, Wawancara, Penawaran,
-- Ditolak, Ditutup.
create table if not exists public.applications (
  id                uuid primary key default gen_random_uuid(),
  user_id           uuid not null default auth.uid() references auth.users (id) on delete cascade,
  company           text not null check (length(trim(company)) between 1 and 200),
  position          text not null check (length(trim(position)) between 1 and 200),
  location          text check (length(location) <= 200),
  source_url        text check (length(source_url) <= 2000),
  applied_at        date,
  stage             text not null default 'prepared'
                    check (stage in ('prepared', 'submitted', 'assessment', 'interview',
                                     'offer', 'rejected', 'closed')),
  stage_changed_at  timestamptz not null default now(),
  notes             text check (length(notes) <= 10000),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  -- Target composite foreign key dari tabel anak, supaya baris anak dijamin
  -- milik pengguna yang sama dengan lamarannya.
  unique (id, user_id)
);

create index if not exists applications_user_stage_idx
  on public.applications (user_id, stage);

-- Riwayat perubahan tahap. Hanya diisi trigger, pengguna hanya bisa membaca.
create table if not exists public.application_stage_history (
  id              bigint generated always as identity primary key,
  application_id  uuid not null,
  user_id         uuid not null,
  from_stage      text,
  to_stage        text not null,
  changed_at      timestamptz not null default now(),
  foreign key (application_id, user_id)
    references public.applications (id, user_id) on delete cascade
);

create index if not exists application_stage_history_app_idx
  on public.application_stage_history (application_id, changed_at);

-- Jadwal penting per lamaran (tes, wawancara), terpisah dari tahap.
create table if not exists public.application_events (
  id              uuid primary key default gen_random_uuid(),
  application_id  uuid not null,
  user_id         uuid not null default auth.uid(),
  kind            text not null default 'interview'
                  check (kind in ('assessment', 'interview', 'other')),
  title           text not null check (length(trim(title)) between 1 and 200),
  scheduled_at    timestamptz not null,
  notes           text check (length(notes) <= 2000),
  created_at      timestamptz not null default now(),
  foreign key (application_id, user_id)
    references public.applications (id, user_id) on delete cascade
);

create index if not exists application_events_user_time_idx
  on public.application_events (user_id, scheduled_at);

-- RLS: setiap pengguna hanya melihat dan mengubah datanya sendiri.
alter table public.applications enable row level security;
alter table public.application_stage_history enable row level security;
alter table public.application_events enable row level security;

drop policy if exists "applications_own" on public.applications;
create policy "applications_own" on public.applications
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "application_stage_history_select_own" on public.application_stage_history;
create policy "application_stage_history_select_own" on public.application_stage_history
  for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "application_events_own" on public.application_events;
create policy "application_events_own" on public.application_events
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

revoke all on public.applications, public.application_stage_history, public.application_events
  from anon, authenticated;
grant select, insert, update, delete on public.applications to authenticated;
grant select on public.application_stage_history to authenticated;
grant select, insert, update, delete on public.application_events to authenticated;

-- Sebelum simpan: jaga updated_at, catat waktu perubahan tahap, dan isi tanggal
-- melamar otomatis saat lamaran pertama kali ditandai terkirim.
create or replace function public.applications_before_write()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if tg_op = 'UPDATE' then
    new.updated_at = now();
    new.created_at = old.created_at;
    if new.stage is distinct from old.stage then
      new.stage_changed_at = now();
    else
      new.stage_changed_at = old.stage_changed_at;
    end if;
  else
    new.created_at = now();
    new.updated_at = now();
    new.stage_changed_at = now();
  end if;

  if new.stage <> 'prepared' and new.applied_at is null then
    new.applied_at = current_date;
  end if;
  return new;
end;
$$;

drop trigger if exists applications_before_write on public.applications;
create trigger applications_before_write
  before insert or update on public.applications
  for each row execute function public.applications_before_write();

-- Setelah simpan: tulis riwayat tahap. security definer karena pengguna sendiri
-- tidak punya izin insert ke tabel riwayat.
create or replace function public.applications_log_stage()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if tg_op = 'INSERT' or new.stage is distinct from old.stage then
    insert into public.application_stage_history (application_id, user_id, from_stage, to_stage)
    values (new.id, new.user_id, case when tg_op = 'UPDATE' then old.stage end, new.stage);
  end if;
  return null;
end;
$$;

revoke execute on function public.applications_log_stage() from public, anon, authenticated;

drop trigger if exists applications_log_stage on public.applications;
create trigger applications_log_stage
  after insert or update of stage on public.applications
  for each row execute function public.applications_log_stage();
