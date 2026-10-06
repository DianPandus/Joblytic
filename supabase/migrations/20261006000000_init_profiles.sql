-- Fase 0: tabel profil akun (satu baris per pengguna Supabase Auth).
-- Data CV/profil kerja terstruktur menyusul di Fase 1; tabel ini hanya menyimpan
-- identitas akun, peran (user/admin), dan status aktif.

create table if not exists public.profiles (
  id          uuid primary key references auth.users (id) on delete cascade,
  email       text not null,
  full_name   text,
  role        text not null default 'user' check (role in ('user', 'admin')),
  is_active   boolean not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- Pengguna hanya bisa membaca barisnya sendiri.
drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles
  for select to authenticated
  using ((select auth.uid()) = id);

-- Pengguna hanya bisa mengubah barisnya sendiri...
drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
  for update to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- ...dan hanya kolom full_name, supaya tidak bisa menaikkan peran sendiri
-- atau mengaktifkan ulang akun yang dinonaktifkan admin.
revoke insert, update, delete on public.profiles from anon, authenticated;
grant select on public.profiles to authenticated;
grant update (full_name) on public.profiles to authenticated;

-- Jaga updated_at.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

-- Buat baris profil otomatis saat pengguna mendaftar.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    nullif(new.raw_user_meta_data ->> 'full_name', '')
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Fungsi kecil untuk health check backend: menyentuh database tanpa membuka data
-- pengguna, sekaligus mencegah proyek free tier dijeda karena tidak aktif.
create or replace function public.ping()
returns text
language sql
stable
set search_path = ''
as $$ select 'pong'::text $$;

grant execute on function public.ping() to anon, authenticated;
