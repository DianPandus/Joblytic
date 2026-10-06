# Joblytic

Asisten lamaran kerja: menilai kecocokan CV dengan lowongan, menunjukkan gap skill, menyarankan perbaikan CV yang tetap bersumber dari profil pengguna, dan melacak status setiap lamaran. Spesifikasi lengkap ada di [`PRD Joblytic.md`](./PRD%20Joblytic.md).

**Status:** Fase 0, kerangka web & deploy.

## Struktur

```
frontend/              Next.js 16 (App Router) + Tailwind + Supabase Auth  → Vercel
backend/               FastAPI + verifikasi JWT Supabase                    → Render (free)
supabase/migrations/   Skema Postgres + row-level security                  → Supabase (free)
.github/workflows/     CI (lint, test, build) dan keep-alive terjadwal
render.yaml            Blueprint deploy backend di Render
```

Alur autentikasi: frontend login lewat Supabase Auth → access token (JWT) dikirim ke backend sebagai `Authorization: Bearer` → backend memverifikasi tanda tangan JWT (JWKS asimetris, atau legacy HS256), lalu membaca database memakai token pengguna yang sama sehingga RLS tetap berlaku. Peran admin diperiksa di backend (`require_admin`), bukan hanya di tampilan.

## Menjalankan lokal

Prasyarat: Node 20+, Python 3.11+, satu proyek Supabase (lihat langkah setup di bawah).

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env            # isi SUPABASE_URL & SUPABASE_PUBLISHABLE_KEY
uvicorn app.main:app --reload   # http://localhost:8000/docs
pytest

# Frontend
cd frontend
npm install
cp .env.example .env.local      # isi variabel NEXT_PUBLIC_*
npm run dev                     # http://localhost:3000
```

## Setup & deploy (semua free tier)

### 1. Supabase
1. Buat proyek di <https://supabase.com/dashboard> (region Singapore).
2. **SQL Editor** → jalankan isi `supabase/migrations/20261006000000_init_profiles.sql`.
3. **Project Settings → API Keys**: catat Project URL dan *publishable key*.
4. **Authentication → URL Configuration**: Site URL = URL Vercel, tambahkan Redirect URL `http://localhost:3000/auth/confirm` dan `https://<app>.vercel.app/auth/confirm`.
5. Jadikan akun sendiri admin (setelah mendaftar):
   ```sql
   update public.profiles set role = 'admin' where email = 'email-kamu@contoh.com';
   ```

### 2. Backend di Render
1. Push repo ke GitHub.
2. Render → **New → Blueprint** → pilih repo (membaca `render.yaml`).
3. Isi env: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `CORS_ORIGINS=https://<app>.vercel.app,http://localhost:3000`. `SUPABASE_JWT_SECRET` hanya untuk proyek lama yang masih HS256.
4. Cek `https://<api>.onrender.com/health?deep=true` → `{"status":"ok","database":"ok"}`.

### 3. Frontend di Vercel
1. Vercel → **Add New Project** → repo ini, **Root Directory = `frontend`**.
2. Env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_API_URL=https://<api>.onrender.com`.
3. Deploy, lalu perbarui Site URL/Redirect URL di Supabase dan `CORS_ORIGINS` di Render bila URL berubah.

### 4. GitHub
- Settings → Secrets and variables → Actions → **Variables**: `BACKEND_URL=https://<api>.onrender.com` untuk workflow keep-alive.

## Syarat selesai Fase 0

- [x] Repo frontend & backend, migrasi database dengan RLS, CI
- [ ] Supabase, Render, dan Vercel terhubung
- [ ] Pengguna bisa daftar dan login di URL publik, profil tersimpan di tabel `profiles`, dan kartu "Server API" di dashboard menunjukkan *Terhubung*

## Catatan free tier

- Backend Render tidur setelah 15 menit tanpa trafik dan butuh ~1 menit untuk bangun; dashboard menampilkan status "Menghubungkan ke server…".
- Supabase dijeda setelah seminggu tidak aktif; workflow `keepalive.yml` mem-ping `/health?deep=true` setiap 2 hari.
