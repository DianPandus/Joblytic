# Set evaluasi ekstraksi lowongan

Target PRD: akurasi ≥ 90% per field pada 30 lowongan berlabel.

## Menambah lowongan

1. Salin teks lowongan asli **apa adanya** ke `postings/<nama>.txt` (UTF-8), mis. `postings/01-data-analyst-tokopedia.txt`. Variasikan sumber (Jobstreet, Glints, LinkedIn, situs karier perusahaan), bahasa (Indonesia/Inggris), dan bidang.
2. Dari folder `backend`: `python -m evals.job_extraction draft` membuat `labels/<nama>.json` dari keluaran model.
3. Koreksi setiap draf terhadap teks lowongannya mengikuti aturan di bawah, lalu ubah `"verified": false` menjadi `true`. Draf yang belum diverifikasi tidak ikut dinilai.
4. `python -m evals.job_extraction run` menilai semua label terverifikasi dan menyimpan hasilnya di `results/`.

Draf hanya untuk menghemat ketikan. Label harus mencerminkan teks lowongan, bukan keluaran model, jadi periksa setiap field, termasuk yang tampak benar.

## Aturan label

| Field | Isi | Kosong bila |
|---|---|---|
| `position` | Judul posisi utuh seperti tertulis, termasuk jenjang/divisi/kode di judul ("Fresh Graduate Business Analyst", "Backend Developer - Java - ADMO") | — |
| `company` | Perusahaan yang merekrut | disamarkan/tidak disebut → `null` |
| `location` | Kota/negara penempatan atau "Remote", disalin seperti tertulis ("Jakarta Selatan, Jakarta Raya"). Unit bisnis tempat penempatan bukan lokasi | tidak disebut → `null` |
| `required_skills` | Skill yang diminta di kualifikasi atau tanggung jawab: bahasa pemrograman, tools, software, metode, bidang keahlian, bahasa (English, Mandarin). Dari tanggung jawab hanya tools/teknologi/metode yang disebut namanya, bukan aktivitas kerja. Satu skill per item, ditulis seperti di teks tanpa kata sifat ("Fluent English" → `"English"`), gabungan dipisah, termasuk di dalam kurung ("Python/R" → `"Python"`, `"R"`; "Message Broker (Kafka / RabbitMQ)" → tiga item), singkatan dalam kurung dan versi tetap satu item (`"Large Language Models (LLM)"`, `".NET 5"`) | `[]` |
| `preferred_skills` | Skill bertanda plus, preferred, nice to have, diutamakan, nilai tambah | `[]` |
| `education_level` | Jenjang minimal: `sma`, `d3`, `d4`, `s1`, `s2`, `s3`. Bila beberapa diterima (D3/S1), pilih yang terendah | `null` |
| `education_fields` | Nama jurusan yang disebut, seperti tertulis; "bidang terkait"/"related field" tidak dihitung | semua jurusan/tidak disebut → `[]` |
| `min_experience_years` | Angka tahun minimal (6 bulan = `0.5`). Angka tahun yang tertulis diutamakan; tanpa angka, `0` bila fresh graduate/lulusan baru dipersilakan (termasuk label kategori "Lulusan Baru"), walau pengalaman disebut nilai tambah. Syarat berbeda per jenjang → pakai yang sesuai judul posisi | tidak disebut → `null` |
| `responsibilities` | Butir tanggung jawab, disalin apa adanya | `[]` |

Yang **bukan** skill: soft skill dan sifat pribadi (komunikasi, problem-solving, analitis, berpikir kritis, kepemimpinan, integritas, mentoring; sejak `job-extract-v3`), usia, domisili, SIM, kesediaan ditempatkan, status kesehatan, frasa umum ("bahasa pemrograman lain"), dan daftar dari tampilan situs seperti bagian "Bagaimana Anda cocok" di Jobstreet.

## Cara menilai

- Field tunggal: akurasi, cocok bila sama setelah huruf kecil, spasi, dan tanda baca diabaikan. Angka harus sama persis.
- Field daftar: F1 mikro atas semua lowongan (tiap item label hanya bisa dipasangkan sekali). Field skill dan `responsibilities` boleh sedikit beda redaksi (kemiripan ≥ 85%); untuk skill, kata pengantar seperti good/strong/fluent/skills/kemampuan diabaikan dulu, dan singkatan dianggap sama dengan kepanjangannya ("UAT" = "User Acceptance Testing", sejak `job-extract-v5`). Berlaku sejak `job-extract-v2`; hasil v1 memakai pencocokan persis untuk skill, jadi angkanya tidak bisa dibandingkan langsung. Kedua sisi kosong dihitung benar.
- Lowongan yang gagal diekstrak dicatat terpisah dan tidak masuk skor.

## Hasil

`gemini-3.5-flash-lite`, prompt `job-extract-v5`, 18 lowongan berlabel (Oktober 2026). Belum 30 lowongan seperti target PRD.

| Field | Metrik | Skor | Target 90% |
|---|---|---|---|
| `position` | akurasi | 94,4% | lulus |
| `company` | akurasi | 100% | lulus |
| `location` | akurasi | 100% | lulus |
| `education_level` | akurasi | 100% | lulus |
| `min_experience_years` | akurasi | 94,4% | lulus |
| `required_skills` | F1 | 89,8% (P 0,89 / R 0,90) | belum |
| `preferred_skills` | F1 | 81,6% | belum |
| `education_fields` | F1 | 100% | lulus |
| `responsibilities` | F1 | 100% | lulus |

Catatan membaca angka ini:

- Prompt v1 sampai v5 disetel memakai 18 lowongan yang sama, jadi angkanya cenderung optimistis. Lowongan baru yang ditambahkan sebaiknya dinilai dulu tanpa mengubah prompt.
- Skor `preferred_skills` dinilai ulang dari prediksi run v5 setelah nama sertifikasi di label `devops-engineer-jobstreet` dikoreksi menjadi utuh seperti tertulis; file di `results/` mencatat 77,7% sebelum koreksi itu.
- Hasil Gemini tidak sepenuhnya deterministik walau temperature 0; antar-run bisa bergeser 1-3 poin.
- Sisa kesalahan skill sebagian besar soal batas label (mis. item di bagian preferred yang berupa topik proyek, atau aktivitas di paragraf "Work you'll do"), bukan skill yang salah dibaca.
