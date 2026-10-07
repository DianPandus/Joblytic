# Joblytic

Asisten lamaran kerja: menilai kecocokan CV dengan lowongan, menunjukkan gap skill, menyarankan perbaikan CV yang tetap bersumber dari profil pengguna, dan melacak status setiap lamaran. Spesifikasi lengkap ada di [`PRD Joblytic.md`](./PRD%20Joblytic.md).

**Status:** Fase 0 selesai (live di <https://joblytic-eta.vercel.app>). Fase 1 berjalan: tracker lamaran sudah ada; unggah dan ekstraksi CV menyusul.

## Struktur

```
frontend/              Next.js 16 (App Router) + Tailwind + Supabase Auth  → Vercel
backend/               FastAPI + verifikasi JWT Supabase                    → Railway
supabase/migrations/   Skema Postgres + row-level security                  → Supabase (free)
.github/workflows/     CI (lint, test, build) dan keep-alive terjadwal
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
2. **SQL Editor** → jalankan isi setiap file di `supabase/migrations/` berurutan sesuai nama file (aman dijalankan ulang).
3. **Project Settings → API Keys**: catat Project URL dan *publishable key*.
4. **Authentication → URL Configuration**: Site URL = URL Vercel, tambahkan Redirect URL `http://localhost:3000/auth/confirm` dan `https://<app>.vercel.app/auth/confirm`.
5. Jadikan akun sendiri admin (setelah mendaftar):
   ```sql
   update public.profiles set role = 'admin' where email = 'email-kamu@contoh.com';
   ```

### 2. Backend di Railway
1. Railway → **New Project → Deploy from GitHub repo** → pilih repo ini.
2. Service → **Settings** (build pertama akan gagal sebelum Root Directory diisi; isi lalu redeploy):
   - Root Directory: `backend`
   - Custom Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Healthcheck Path: `/health`
   - Serverless (App Sleeping): **ON**, agar kredit gratis cukup
3. **Variables**: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `CORS_ORIGINS=https://<app>.vercel.app,http://localhost:3000`. `SUPABASE_JWT_SECRET` hanya untuk proyek lama yang masih HS256. Perubahan variable baru berlaku setelah klik **Deploy** di banner "Apply changes".
4. **Settings → Networking → Generate Domain**, lalu cek `https://<api>.up.railway.app/health?deep=true` → `{"status":"ok","database":"ok"}`. Selain `ok`, field `database` menyebut penyebabnya (`not_configured`, `http_401`, `unreachable (...)`).

### 3. Frontend di Vercel
1. Vercel → **Add New Project** → repo ini, **Root Directory = `frontend`**.
2. Env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `NEXT_PUBLIC_API_URL=https://<api>.up.railway.app` (wajib diawali `https://`; tanpa itu request jadi path relatif dan berakhir 404 di Vercel).
3. Variable `NEXT_PUBLIC_*` ditanam saat build, jadi setiap mengubahnya harus **Redeploy**.
4. Perbarui Site URL/Redirect URL di Supabase dan `CORS_ORIGINS` di Railway bila URL berubah.

### 4. GitHub
- Settings → Secrets and variables → Actions → **Variables**: `BACKEND_URL=https://<api>.up.railway.app` untuk workflow keep-alive.

## Syarat selesai Fase 0

- [x] Repo frontend & backend, migrasi database dengan RLS, CI
- [x] Supabase, Railway, dan Vercel terhubung
- [x] Pengguna bisa daftar dan login di URL publik, profil tersimpan di tabel `profiles`, dan kartu "Server API" di dashboard menunjukkan *Terhubung*

## Catatan free tier

- Railway: trial $5 selama 30 hari tanpa kartu, lalu Free plan dengan kredit $1/bulan dan RAM 0,5 GB. Mode serverless menidurkan backend saat sepi; dashboard menampilkan status "Menghubungkan ke server…" selama backend bangun. RAM 0,5 GB perlu dievaluasi ulang sebelum Fase 3 (model embedding).
- Supabase dijeda setelah seminggu tidak aktif; workflow `keepalive.yml` mem-ping `/health?deep=true` setiap 2 hari.
