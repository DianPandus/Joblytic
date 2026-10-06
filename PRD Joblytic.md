# PRD: Asisten Lamaran Kerja

Oct 6, 2026 · @dian ramboy

## 1. Ringkasan

Produk ini adalah aplikasi web yang membantu pencari kerja mengelola banyak lamaran sekaligus: menilai kecocokan CV dengan sebuah lowongan, menunjukkan gap skill, menyarankan perbaikan CV, dan melacak status tiap lamaran dari awal sampai hasil akhir. Produk dibangun sebagai website multi-user sungguhan (frontend, backend, database cloud, dan panel admin) yang seluruhnya berjalan di free tier, dengan target awal pencari kerja di bidang software, data, dan AI di Indonesia, termasuk pemilik proyek sebagai pengguna pertama.

Prinsip desainnya sama dengan proyek InveSTudy: bagian yang butuh kepastian (skor kecocokan, status, tanggal) dihitung secara deterministik, sedangkan LLM hanya dipakai untuk memahami teks (mengekstrak persyaratan lowongan) dan menjelaskan hasil. Semua saran perbaikan CV wajib bersumber dari fakta yang memang ada di profil pengguna, tidak boleh mengarang pengalaman.

## 2. Latar Belakang & Masalah

Pencari kerja fresh graduate biasanya melamar belasan posisi sekaligus, dan informasinya tercecer di banyak tempat: lowongan di berbagai situs, versi CV yang berbeda-beda, serta jadwal tes dan wawancara yang tersebar di email dan chat. Akibatnya:

- Sulit menilai cepat apakah sebuah lowongan layak dikejar, atau skill apa yang masih kurang dibanding persyaratannya
- CV dikirim hampir sama untuk semua lowongan karena menyesuaikannya manual itu lama
- Status lamaran (sudah kirim, tahap tes, jadwal wawancara, menunggu hasil) mudah terlewat, apalagi tiap perusahaan punya tahapan berbeda
- Alat bantu AI umum (chatbot biasa) bisa membuat saran perbaikan CV, tetapi sering menambahkan klaim yang tidak pernah dilakukan pengguna, dan tidak menyimpan riwayat lamaran

Masalah intinya: pencocokan CV dengan lowongan butuh penilaian yang konsisten dan bisa dijelaskan, serta pelacakan yang terstruktur. Keduanya tidak terselesaikan oleh satu chatbot tanpa data terstruktur di belakangnya.

## 3. Tujuan

**Tujuan produk:**

- Pengguna bisa menempelkan deskripsi lowongan dan mendapat skor kecocokan beserta rinciannya (skill yang cocok, yang kurang, dan alasannya) dalam waktu singkat
- Pengguna mendapat saran penyesuaian CV per lowongan yang seluruhnya bersumber dari profilnya sendiri
- Pengguna bisa melihat semua lamaran, tahap, dan jadwal pentingnya di satu tempat

**Tujuan portofolio:**

- Menunjukkan desain sistem LLM yang memisahkan bagian deterministik dari bagian generatif, dengan evaluasi terukur
- Menunjukkan kemampuan web end-to-end: frontend, backend API, autentikasi multi-user, database cloud, panel admin, dan deployment, semuanya di free tier
- Produk dipakai sungguhan oleh pemilik dan beberapa pengguna lain, sehingga ada cerita pengguna nyata untuk interview

## 4. Non-Goals (Di Luar Scope)

MVP sengaja tidak mengirim lamaran apa pun atas nama pengguna; keputusan melamar dan tombol kirim tetap di tangan pengguna.

- **Bukan** fitur kirim lamaran otomatis atau pengisian formulir di portal perusahaan
- Tidak scraping portal lowongan yang butuh login (misalnya LinkedIn); lowongan dimasukkan lewat tempel teks atau tautan publik
- Tidak menjanjikan atau memprediksi peluang diterima; skor kecocokan hanya alat bantu prioritas
- Tidak ada pembayaran atau langganan, dan tidak dirancang untuk skala besar; targetnya puluhan sampai ratusan pengguna di free tier
- Tidak mencakup latihan wawancara atau simulasi tes (kandidat stretch goal)
- Tidak membuat CV dari nol; sistem hanya menyesuaikan dan menyarankan dari profil yang sudah diisi pengguna

## 5. Target Pengguna

Pengguna utama adalah fresh graduate yang sedang aktif melamar banyak posisi sekaligus.

- **Primary persona**: fresh graduate bidang IT/data/AI di Indonesia yang melamar 10-30 posisi di berbagai jenis perusahaan (BUMN, bank, startup, korporasi) dengan tahapan seleksi berbeda-beda (tes online, asesmen, wawancara). Ia punya CV dan portofolio, tetapi kesulitan menyesuaikan dan memantau semuanya.
- **Secondary persona (konteks portofolio)**: reviewer teknis (interviewer atau recruiter) yang menilai kemampuan engineering dari proyek ini, terutama desain sistem, evaluasi, dan demo yang berjalan.

* **Admin**: pemilik proyek yang memantau jumlah pengguna, aktivitas analisis, pemakaian kuota LLM, dan error lewat panel admin; admin hanya melihat statistik agregat, bukan isi CV pengguna.

## 6. User Stories

Sepuluh user story berikut mencakup alur utama dari daftar akun dan unggah CV sampai memantau hasil lamaran, serta kebutuhan pengguna atas data mereka dan kebutuhan admin.

| ID | Sebagai... | Saya ingin... | Supaya... | Acceptance criteria |
| --- | --- | --- | --- | --- |
| US-1 | Pencari kerja | mengunggah CV satu kali dan profil terisi otomatis dari isinya | semua analisis memakai data yang sama dan konsisten | Profil terisi dari CV yang diunggah; field yang tidak ada di CV dibiarkan kosong, tidak ditebak LLM; setiap entri bisa dikoreksi dan profil bisa diekspor |
| US-2 | Pencari kerja | menempelkan deskripsi lowongan | persyaratannya terbaca otomatis tanpa menyalin manual | Sistem mengekstrak posisi, perusahaan, skill wajib, skill nilai tambah, dan syarat pendidikan/pengalaman; hasil bisa dikoreksi manual |
| US-3 | Pencari kerja | melihat skor kecocokan CV dengan lowongan | memprioritaskan lowongan yang paling layak dikejar | Skor 0-100 dengan rincian per kategori; setiap poin menunjuk ke bagian profil dan persyaratan terkait |
| US-4 | Pencari kerja | melihat daftar gap skill untuk sebuah lowongan | tahu apa yang perlu dipelajari atau disorot | Daftar skill yang diminta tetapi tidak ditemukan di profil, dipisah antara wajib dan nilai tambah |
| US-5 | Pencari kerja | mendapat saran penyesuaian poin CV untuk lowongan tertentu | CV lebih relevan tanpa menulis ulang dari nol | Setiap saran mengutip entri profil sumbernya; saran yang menambah fakta baru ditolak sistem |
| US-6 | Pencari kerja | mencatat dan mengubah tahap tiap lamaran beserta tanggalnya | tidak ada jadwal tes atau wawancara yang terlewat | Tahap, tanggal, dan catatan tersimpan per lamaran; riwayat perubahan tahap terlihat |
| US-7 | Pencari kerja | melihat ringkasan semua lamaran di dashboard | memahami posisi saya secara keseluruhan | Dashboard menampilkan jumlah lamaran per tahap, jadwal terdekat, dan lamaran yang lama tidak ada kabar |
| US-8 | Pengguna baru | mendaftar dan masuk ke akun saya | CV dan data lamaran saya tersimpan aman dan hanya saya yang bisa melihatnya | Daftar dan login berjalan (email dan password, login Google opsional); setiap data terikat ke pemiliknya; pengguna lain tidak bisa mengakses data saya |
| US-9 | Pengguna | menghapus akun beserta CV dan seluruh data saya | saya mengendalikan data pribadi saya | Penghapusan akun menghapus profil, berkas CV, analisis, dan lamaran; ada konfirmasi sebelum dihapus |
| US-10 | Admin | melihat statistik penggunaan di panel admin | tahu berapa banyak orang yang memakai website dan apakah kuota gratis masih cukup | Panel menampilkan jumlah pengguna terdaftar, pengguna aktif, analisis per hari, pemakaian kuota LLM, dan error terbaru; hanya akun berperan admin yang bisa membuka; isi CV tidak ditampilkan |

## 7. Functional Requirements

**7.1 Profil & CV**

- Pengguna mengunggah CV (PDF atau Word); sistem mengekstrak isinya ke profil terstruktur: pendidikan, pengalaman, organisasi, proyek, skill, sertifikasi, dan bahasa
- Setiap butir pengalaman atau proyek disimpan sebagai entri tersendiri dengan ID, supaya bisa dirujuk oleh saran dan skor
- Hasil ekstraksi ditampilkan untuk dikoreksi; field yang tidak ada di CV dibiarkan kosong dan tidak ditebak oleh LLM. Bila sebuah lowongan mensyaratkan data yang masih kosong (misalnya pengalaman organisasi), sistem meminta pengguna mengisinya langsung di web; jika pengguna memang tidak punya, field tetap kosong. Profil bisa diekspor ke format teks atau Markdown

**7.2 Analisis Lowongan**

- Pengguna menempelkan teks deskripsi lowongan (atau tautan publik, bila bisa diambil)
- LLM mengekstrak ke skema terstruktur (divalidasi Pydantic): nama posisi, perusahaan, lokasi, skill wajib, skill nilai tambah, syarat pendidikan, syarat pengalaman, tanggung jawab utama
- Hasil ekstraksi ditampilkan dan bisa dikoreksi pengguna sebelum dipakai untuk pencocokan
- Jika ekstraksi gagal validasi, sistem mengulang dengan prompt yang lebih ketat sebelum menyerah

**7.3 Pencocokan & Gap Analysis**

- Sistem menghitung skor kecocokan secara deterministik dari data terstruktur: kecocokan skill (eksak dan semantik lewat embedding), kecocokan pendidikan, dan relevansi pengalaman/proyek
- Bobot tiap kategori terlihat dan bisa diatur pengguna
- Rincian skor menunjukkan skill yang cocok beserta entri profil pendukungnya, dan skill yang belum ditemukan
- LLM hanya dipakai untuk menyusun penjelasan dalam bahasa natural dari rincian tersebut, bukan untuk menentukan angka

**7.4 Saran Penyesuaian CV (Grounded)**

- Sistem menyarankan penyusunan ulang atau penekanan butir CV yang relevan dengan lowongan
- Setiap saran harus menyertakan ID entri profil sumbernya
- Validator memeriksa bahwa saran tidak memuat skill, angka, atau pengalaman yang tidak ada di profil; saran yang melanggar dibuang atau ditandai
- Saran bersifat usulan; pengguna yang memutuskan memakainya atau tidak

**7.5 Tracker Lamaran**

- Setiap lamaran punya: perusahaan, posisi, tautan/sumber, tanggal melamar, tahap saat ini, dan catatan
- Tahap yang disediakan dan bisa diubah: Disiapkan, Dikirim, Tes/Asesmen, Wawancara, Penawaran, Ditolak, Ditutup
- Setiap perubahan tahap dicatat dengan tanggal; jadwal tes atau wawancara bisa disimpan sebagai tanggal terpisah
- Lamaran terhubung ke hasil analisis lowongan dan skor kecocokannya

**7.6 Dashboard**

- Ringkasan jumlah lamaran per tahap
- Daftar jadwal terdekat (tes, wawancara)
- Daftar lamaran tanpa perubahan lebih dari jumlah hari tertentu
- Perbandingan skor kecocokan antar lowongan yang sedang dipertimbangkan

**7.7 Interface**

- Satu aplikasi web (frontend terpisah dari backend) dengan navigasi antara Profil, Analisis Lowongan, Tracker, dan Dashboard; halaman admin berada di jalur terpisah dan hanya bisa dibuka admin
- Alur analisis: tempel lowongan, koreksi hasil ekstraksi, lihat skor, saran, dan simpan sebagai lamaran

**7.8 Akun & Autentikasi**

- Pengguna mendaftar dan masuk dengan email dan password (login Google opsional); backend memverifikasi token di setiap permintaan
- Setiap data (profil, CV, analisis, lamaran) terikat ke pemiliknya dan hanya bisa diakses pemiliknya, ditegakkan di database lewat row-level security dan di backend
- Pengguna bisa menghapus akun beserta berkas CV dan seluruh datanya
- Saat mengunggah CV, pengguna membaca dan menyetujui pemberitahuan bahwa teks CV diproses oleh penyedia LLM pihak ketiga

**7.9 Panel Admin**

- Hanya akun berperan admin yang bisa membuka halaman admin; peran diperiksa di backend, bukan hanya disembunyikan di tampilan
- Menampilkan jumlah pengguna terdaftar, pengguna aktif harian dan mingguan, jumlah analisis per hari, pemakaian kuota LLM, dan daftar error terbaru
- Admin hanya melihat statistik agregat, bukan isi CV atau lamaran pengguna
- Admin bisa menonaktifkan akun yang menyalahgunakan layanan

**7.10 Batas Pemakaian**

- Batas analisis per pengguna per hari dan batas ukuran file CV, karena kuota LLM gratis dipakai bersama semua pengguna
- Saat kuota habis, sistem menampilkan pesan yang jelas, bukan gagal diam-diam
- Hasil ekstraksi untuk lowongan yang sama disimpan (cache) agar LLM tidak dipanggil berulang

## 8. Non-Functional Requirements

- **Grounding**: tidak boleh ada klaim pengalaman, skill, atau angka dalam saran CV yang tidak berasal dari profil pengguna (target pelanggaran: 0 pada set evaluasi)
- **Akurasi skor**: skor dan rinciannya dihitung dari data terstruktur dengan kode, sehingga input yang sama selalu menghasilkan skor yang sama
- **Transparansi**: setiap skor bisa dijelaskan sampai ke skill dan entri profil yang mendasarinya
- **Privasi**: CV berisi data pribadi, jadi identitas (nama, nomor telepon, email, alamat) dihapus dari teks sebelum dikirim ke LLM API, pengguna wajib menyetujui pemberitahuan pemrosesan oleh pihak ketiga, data tiap pengguna terisolasi, dan akun beserta datanya bisa dihapus kapan saja
- **Performa**: analisis satu lowongan selesai di bawah 15 detik untuk MVP, di luar cold start server yang sekitar satu menit
- **Biaya**: seluruh komponen (hosting, database, penyimpanan file, LLM) memakai free tier sehingga biaya bulanan Rp 0; kuota LLM gratis dipakai bersama semua pengguna, jadi panggilan dibatasi satu ekstraksi dan satu penjelasan per lowongan, dengan cache hasil dan batas pemakaian harian per pengguna
- **Reproducibility**: pipeline bisa dijalankan ulang untuk lowongan atau profil baru tanpa mengubah kode inti, dan versi prompt serta model tercatat di tiap hasil analisis

* **Keamanan**: autentikasi wajib untuk semua endpoint data, peran admin diperiksa di backend, kunci API LLM dan kunci database hanya ada di environment variable server, komunikasi lewat HTTPS, dan tipe serta ukuran file CV yang diunggah divalidasi
* **Ketersediaan**: backend di free tier tidur setelah 15 menit tanpa lalu lintas dan butuh sekitar satu menit untuk bangun, dan database free tier dijeda setelah seminggu tidak aktif; antarmuka menampilkan status menghubungkan dan ada health check berkala agar tidak terlihat rusak

## 9. Arsitektur & Tech Stack

LLM dipakai di dua titik saja, yaitu mengekstrak persyaratan lowongan dan menjelaskan hasil; skor dan validasi grounding dijalankan kode, dan profil yang sama dipakai untuk menolak saran yang mengarang fakta.

&#91;embedded content: alur analisis lowongan · 2 titik LLM, 2 komponen kode\]

Pengguna mengoreksi hasil ekstraksi sebelum masuk ke mesin skor, sehingga kesalahan LLM tidak langsung mempengaruhi angka.

&#91;embedded content: arsitektur sistem · frontend, backend, Supabase, LLM API\]

Pengguna dan admin membuka frontend yang sama; backend memeriksa token dan peran di setiap permintaan, sedangkan Supabase menyimpan akun, data, dan berkas CV.

**Tech stack (usulan, mengikuti stack InveSTudy agar bisa dipakai ulang):**

| Lapisan | Pilihan | Catatan |
| --- | --- | --- |
| Backend | FastAPI | Endpoint analisis, profil, tracker, dan admin; berjalan di Render (free web service) |
| Validasi data | Pydantic v2 | Skema ekstraksi dan retry bila output rusak |
| Database | Supabase Postgres (free tier) | Mendukung banyak pengguna dengan isolasi data per pengguna; SQLite tidak dipakai karena disk di free hosting tidak permanen. Free tier: 500 MB, dijeda setelah seminggu tidak aktif, tanpa backup otomatis |
| Autentikasi | Supabase Auth (email, login Google opsional) | Backend memverifikasi token (JWT) dan peran admin; free tier mencakup 50.000 pengguna aktif bulanan |
| File storage | Supabase Storage | Menyimpan CV asli per pengguna dengan kontrol akses; free tier 1 GB dan maksimal 50 MB per file |
| Hosting | Vercel (frontend) dan Render free web service (backend) | Backend tidur setelah 15 menit tanpa lalu lintas dan butuh sekitar satu menit untuk bangun; database tetap di Supabase karena Postgres gratis Render kedaluwarsa 30 hari; Render menyebut free instance untuk hobi dan uji coba, bukan produksi |
| Embedding | paraphrase-multilingual-MiniLM-L12-v2 | Mendukung bahasa Indonesia; model berjalan di backend dan memakan memori, jadi cek dulu muat tidaknya di free tier (alternatif: embedding API gratis); tanpa vector store karena jumlah skill kecil |
| LLM | Gemini API free tier (model Flash) | Lewat lapisan adapter agar penyedia mudah diganti; kuota gratis dipakai bersama semua pengguna. Free tier Gemini boleh memakai masukan untuk memperbaiki produk Google, jadi identitas di CV dihapus sebelum dikirim (lihat risiko) |
| Frontend | Next.js (React) + Tailwind di Vercel (free) | Web app terpisah dari backend, termasuk halaman admin; pilihan framework final ada di open questions |
| Testing | pytest + GitHub Actions | Termasuk skrip evaluasi dengan set berlabel |

**Entitas data inti:** entri profil, lowongan (hasil ekstraksi), analisis (skor, rincian, versi prompt dan model), lamaran, riwayat tahap, serta pengguna (akun dan peran), berkas CV, dan log pemakaian untuk panel admin; setiap tabel punya kolom pemilik (user\_id) agar data tiap pengguna terisolasi.

**Sumber** (dibuka Oktober 2026; batas free tier bisa berubah, cek ulang sebelum dipakai): [Supabase Pricing](https://supabase.com/pricing), [Gemini API Additional Terms of Service](https://ai.google.dev/gemini-api/terms), [Render: Deploy for Free](https://render.com/docs/free).

## 10. Success Metrics

Metrik produk diukur pada set evaluasi kecil yang dilabel sendiri oleh pemilik; targetnya perlu dikoreksi setelah ada data awal.

**Metrik produk:**

| Metrik | Cara ukur | Target |
| --- | --- | --- |
| Akurasi ekstraksi lowongan | Kecocokan field (skill wajib, syarat pendidikan, dll.) terhadap label manual pada 30 lowongan | ≥ 90% per field |
| Kesesuaian peringkat skor | Korelasi peringkat skor sistem dengan peringkat manual pemilik pada 20 lowongan | ≥ 0.7 (Spearman) |
| Pelanggaran grounding | Jumlah saran CV yang memuat fakta di luar profil, pada 30 saran | 0 |
| Konsistensi skor | Skor yang sama untuk input yang sama pada 10 kali jalan | 100% |
| Waktu analisis | Waktu dari tempel lowongan sampai hasil tampil | < 15 detik |
| Biaya infrastruktur | Tagihan bulanan seluruh layanan | Rp 0 (semua free tier) |

**Metrik portofolio:**

- Proyek selesai sampai fase dashboard dan tracker berjalan end-to-end
- Bisa didemokan live dalam interview, bukan hanya README
- Dipakai untuk melacak minimal 10 lamaran nyata milik pemilik
- Ada cerita teknis yang jelas soal keputusan desain (kenapa skor dihitung deterministik dan LLM hanya mengekstrak serta menjelaskan)

* Website live dengan URL publik dan dipakai minimal 5 pengguna selain pemilik (angka awal, silakan dikoreksi)
* Panel admin menampilkan jumlah pengguna dan pemakaian yang nyata

## 11. Milestone

Pengerjaan dibagi tujuh fase, dimulai dari kerangka web yang sudah live (login, database, deploy), lalu satu irisan tipis end-to-end (tempel lowongan, skor, simpan sebagai lamaran), baru dipoles dan dilengkapi panel admin; total estimasi kasar 7-13 minggu paruh waktu.

| Fase | Output | Syarat selesai | Estimasi |
| --- | --- | --- | --- |
| Fase 0: Kerangka web & deploy | Repo frontend dan backend, login dan database terhubung (Supabase), deploy ke Vercel dan Render, CI sederhana, commit pertama | Pengguna bisa daftar dan login di URL publik, dan data tersimpan di database cloud | 1-2 minggu |
| Fase 1: Fondasi | Skema data (profil, lowongan, lamaran), unggah dan ekstraksi CV ke profil (field kosong dibiarkan), form koreksi profil, tracker dasar, repo dengan commit dan CI sederhana | Profil terisi dari CV yang diunggah dan lamaran bisa dicatat beserta tahapnya lewat antarmuka | 1-2 minggu |
| Fase 2: Ekstraksi lowongan | Pipeline LLM ke skema Pydantic, retry, koreksi manual, set evaluasi 30 lowongan berlabel | Akurasi ekstraksi terukur dan tercatat | 1-2 minggu |
| Fase 3: Pencocokan & gap | Mesin skor deterministik, embedding untuk kecocokan semantik, rincian skor, daftar gap | Skor konsisten dan korelasi peringkat terukur | 1-2 minggu |
| Fase 4: Saran CV grounded | Penghasil saran dengan rujukan entri, validator grounding, evaluasi 30 saran | 0 pelanggaran grounding pada set evaluasi | 1-2 minggu |
| Fase 5: Dashboard & rilis | Dashboard, antarmuka terpadu, dan README dengan angka evaluasi serta demo yang bisa diklik | Bisa didemokan live dari awal sampai akhir | 1 minggu |
| Fase 6: Panel admin & pengamanan | Panel admin (statistik pengguna dan pemakaian), batas pemakaian per pengguna, hapus akun, pemberitahuan privasi dan persetujuan pengguna | Admin bisa melihat statistik; pengguna tidak bisa mengakses data pengguna lain (diuji) | 1-2 minggu |

Estimasi waktu sengaja kasar; sesuaikan dengan kapasitas setelah breakdown task lebih detail.

## 12. Risiko & Asumsi

- **Risiko**: LLM menambahkan klaim yang tidak ada di profil pada saran CV. Mitigasi: setiap saran wajib merujuk ID entri profil, divalidasi dengan kode, dan diuji di set evaluasi dengan target 0 pelanggaran.
- **Risiko**: format lowongan dan CV sangat beragam (poster gambar, PDF hasil scan, CV berkolom atau bertabel, halaman yang butuh login). Mitigasi: MVP hanya menerima teks lowongan yang ditempel dan CV berbasis teks; hasil ekstraksi CV selalu bisa dikoreksi; tautan dan OCR menjadi tahap lanjutan.
- **Risiko**: skor kecocokan terasa subjektif atau menyesatkan. Mitigasi: rincian skor selalu terlihat, bobot bisa diatur, dan skor dikalibrasi terhadap peringkat manual pemilik.
- **Risiko**: data pribadi di CV terkirim ke LLM pihak ketiga, dan pada free tier Gemini masukan boleh dipakai Google untuk memperbaiki produknya dan dibaca reviewer manusia. Mitigasi: identitas dihapus sebelum panggilan API, pengguna wajib menyetujui pemberitahuan di awal, dan pengguna diminta tidak mengunggah data sensitif; bila dinilai belum cukup, pindah ke tier berbayar dengan batas biaya (tidak lagi gratis penuh) atau ke penyedia lain.
- **Risiko**: kuota LLM gratis habis karena dipakai bersama semua pengguna. Mitigasi: batas harian per pengguna, cache hasil ekstraksi, adapter penyedia LLM agar mudah diganti, dan pesan yang jelas saat kuota habis.
- **Risiko**: batas free tier mengganggu pengalaman pengguna (backend tidur, database dijeda, penyimpanan terbatas, database tanpa backup otomatis). Mitigasi: health check dan ping berkala, batas ukuran data per pengguna, ekspor data berkala secara manual, pantauan lewat panel admin, dan cek ulang syarat free tier karena bisa berubah.
- **Risiko**: kebocoran data antar pengguna atau penyalahgunaan (spam unggah, menghabiskan kuota). Mitigasi: isolasi data per pengguna di database, rate limit, validasi file, dan peran admin diperiksa di backend.
- **Risiko**: scope melebar karena sekarang ada frontend, backend, autentikasi, dan admin sekaligus, ditambah godaan auto-apply atau interview coach. Mitigasi: non-goals tegas, kerangka web live lebih dulu (Fase 0), fitur inti dulu, dan panel admin di akhir.
- **Asumsi**: pengguna awal adalah pemilik proyek dan beberapa teman yang mengunggah CV dan menempelkan lowongan sendiri; kualitas dinilai lewat lamaran nyata mereka.
- **Asumsi**: layanan hanya dibuka untuk pengguna di Indonesia, karena ketentuan Gemini API mensyaratkan layanan berbayar bila melayani pengguna di EEA, Swiss, atau Inggris.

## 13. Open Questions

- [x] Nama produk final apa? ("Asisten Lamaran Kerja" masih nama kerja)
- [x] LLM API: Gemini free tier untuk tahap awal (sudah diputuskan); tinjau ulang ke tier berbayar dengan batas biaya bila pengguna bertambah atau data dinilai kurang aman
- [x] Framework frontend: Next.js (React) atau Vite + React?
- [x] Format CV yang didukung untuk diunggah di MVP: PDF saja, atau PDF dan Word? (CV hasil scan butuh OCR)
- [x] Bahasa keluaran: Indonesia saja, atau bisa Inggris untuk lowongan berbahasa Inggris?
- [x] Perlu pengingat jadwal tes dan wawancara (misalnya lewat Telegram) di MVP atau jadi stretch goal?
- [x] Apakah evaluasi (30 lowongan, 30 saran) cukup, atau perlu set yang lebih besar?

* [x] Metode login: email dan password saja, atau ditambah login Google?
* [x] Berapa target pengguna awal (misalnya 10-50 teman dan komunitas) untuk menentukan batas kuota per pengguna?
* [x] Apakah admin benar-benar hanya melihat statistik agregat, atau perlu akses terbatas ke data untuk debugging?
* [x] Pakai domain sendiri atau cukup subdomain gratis dari Vercel?
