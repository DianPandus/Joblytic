-- Fase 1: profil terstruktur dari CV.
-- Setiap entri (pendidikan, pengalaman, proyek, ...) dan setiap butirnya punya ID
-- sendiri, supaya skor (Fase 3) dan saran CV (Fase 4) bisa merujuk sumbernya.

create table if not exists public.profile_entries (
  id            uuid primary key default gen_random_uuid(),
  user_id       uuid not null default auth.uid() references auth.users (id) on delete cascade,
  section       text not null
                check (section in ('education', 'experience', 'organization', 'project',
                                   'skill', 'certification', 'language')),
  -- Nama utama entri: gelar/jurusan, jabatan, nama proyek, nama skill, dst.
  title         text not null check (length(trim(title)) between 1 and 300),
  -- Institusi, perusahaan, organisasi, atau penerbit sertifikat.
  organization  text check (length(organization) <= 300),
  location      text check (length(location) <= 200),
  -- Tanggal di CV biasanya hanya bulan/tahun; disimpan sebagai tanggal 1.
  start_month   date,
  end_month     date,
  is_current    boolean not null default false,
  -- Keterangan singkat: IPK, tingkat kemahiran, kategori skill, dst.
  description   text check (length(description) <= 2000),
  position      integer not null default 0,
  source        text not null default 'manual' check (source in ('cv', 'manual')),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  unique (id, user_id)
);

create index if not exists profile_entries_user_section_idx
  on public.profile_entries (user_id, section, position);

create table if not exists public.profile_bullets (
  id          uuid primary key default gen_random_uuid(),
  entry_id    uuid not null,
  user_id     uuid not null default auth.uid(),
  position    integer not null default 0,
  text        text not null check (length(trim(text)) between 1 and 1000),
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  foreign key (entry_id, user_id)
    references public.profile_entries (id, user_id) on delete cascade
);

create index if not exists profile_bullets_entry_idx
  on public.profile_bullets (entry_id, position);

-- Log unggahan CV: lokasi berkas, persetujuan pemrosesan pihak ketiga, dan versi
-- model/prompt yang dipakai (PRD: reproducibility). Juga dipakai untuk batas harian.
create table if not exists public.cv_uploads (
  id              uuid primary key default gen_random_uuid(),
  user_id         uuid not null default auth.uid() references auth.users (id) on delete cascade,
  storage_path    text not null,
  file_name       text not null,
  mime_type       text not null,
  size_bytes      integer not null,
  consent_at      timestamptz not null,
  llm_model       text,
  prompt_version  text,
  status          text not null default 'processing'
                  check (status in ('processing', 'done', 'failed')),
  error           text,
  created_at      timestamptz not null default now()
);

create index if not exists cv_uploads_user_time_idx
  on public.cv_uploads (user_id, created_at);

alter table public.profile_entries enable row level security;
alter table public.profile_bullets enable row level security;
alter table public.cv_uploads enable row level security;

drop policy if exists "profile_entries_own" on public.profile_entries;
create policy "profile_entries_own" on public.profile_entries
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "profile_bullets_own" on public.profile_bullets;
create policy "profile_bullets_own" on public.profile_bullets
  for all to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

drop policy if exists "cv_uploads_select_own" on public.cv_uploads;
create policy "cv_uploads_select_own" on public.cv_uploads
  for select to authenticated
  using ((select auth.uid()) = user_id);

drop policy if exists "cv_uploads_insert_own" on public.cv_uploads;
create policy "cv_uploads_insert_own" on public.cv_uploads
  for insert to authenticated
  with check ((select auth.uid()) = user_id);

drop policy if exists "cv_uploads_update_own" on public.cv_uploads;
create policy "cv_uploads_update_own" on public.cv_uploads
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

revoke all on public.profile_entries, public.profile_bullets, public.cv_uploads
  from anon, authenticated;
grant select, insert, update, delete on public.profile_entries, public.profile_bullets
  to authenticated;
grant select, insert on public.cv_uploads to authenticated;
grant update (llm_model, prompt_version, status, error) on public.cv_uploads to authenticated;

drop trigger if exists profile_entries_set_updated_at on public.profile_entries;
create trigger profile_entries_set_updated_at
  before update on public.profile_entries
  for each row execute function public.set_updated_at();

drop trigger if exists profile_bullets_set_updated_at on public.profile_bullets;
create trigger profile_bullets_set_updated_at
  before update on public.profile_bullets
  for each row execute function public.set_updated_at();

-- Mengganti seluruh profil dengan hasil ekstraksi CV dalam satu transaksi.
-- security invoker: berjalan dengan hak pengguna, jadi RLS tetap berlaku.
-- Bentuk payload: [{section, title, organization, location, start_month, end_month,
--                   is_current, description, bullets: [text, ...]}, ...]
create or replace function public.replace_profile_from_cv(entries jsonb)
returns integer
language plpgsql
security invoker
set search_path = ''
as $$
declare
  uid uuid := auth.uid();
  item jsonb;
  bullet text;
  v_entry_id uuid;
  entry_pos integer := 0;
  bullet_pos integer;
begin
  if uid is null then
    raise exception 'not authenticated';
  end if;
  if jsonb_typeof(entries) <> 'array' then
    raise exception 'entries must be an array';
  end if;

  delete from public.profile_entries where user_id = uid;

  for item in select * from jsonb_array_elements(entries) loop
    insert into public.profile_entries (
      user_id, section, title, organization, location,
      start_month, end_month, is_current, description, position, source
    ) values (
      uid,
      item ->> 'section',
      item ->> 'title',
      nullif(item ->> 'organization', ''),
      nullif(item ->> 'location', ''),
      (item ->> 'start_month')::date,
      (item ->> 'end_month')::date,
      coalesce((item ->> 'is_current')::boolean, false),
      nullif(item ->> 'description', ''),
      entry_pos,
      'cv'
    ) returning id into v_entry_id;
    entry_pos := entry_pos + 1;

    bullet_pos := 0;
    for bullet in
      select jsonb_array_elements_text(coalesce(item -> 'bullets', '[]'::jsonb))
    loop
      insert into public.profile_bullets (entry_id, user_id, position, text)
      values (v_entry_id, uid, bullet_pos, bullet);
      bullet_pos := bullet_pos + 1;
    end loop;
  end loop;

  return entry_pos;
end;
$$;

revoke execute on function public.replace_profile_from_cv(jsonb) from public, anon;
grant execute on function public.replace_profile_from_cv(jsonb) to authenticated;

-- Bucket privat untuk berkas CV asli: maksimal 5 MB, hanya PDF dan DOCX.
-- Setiap pengguna hanya bisa mengakses folder bernama user id-nya sendiri.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'cvs', 'cvs', false, 5242880,
  array['application/pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
)
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "cvs_select_own" on storage.objects;
create policy "cvs_select_own" on storage.objects
  for select to authenticated
  using (bucket_id = 'cvs' and (storage.foldername(name))[1] = (select auth.uid())::text);

drop policy if exists "cvs_insert_own" on storage.objects;
create policy "cvs_insert_own" on storage.objects
  for insert to authenticated
  with check (bucket_id = 'cvs' and (storage.foldername(name))[1] = (select auth.uid())::text);

drop policy if exists "cvs_update_own" on storage.objects;
create policy "cvs_update_own" on storage.objects
  for update to authenticated
  using (bucket_id = 'cvs' and (storage.foldername(name))[1] = (select auth.uid())::text)
  with check (bucket_id = 'cvs' and (storage.foldername(name))[1] = (select auth.uid())::text);

drop policy if exists "cvs_delete_own" on storage.objects;
create policy "cvs_delete_own" on storage.objects
  for delete to authenticated
  using (bucket_id = 'cvs' and (storage.foldername(name))[1] = (select auth.uid())::text);
