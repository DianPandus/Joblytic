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
| `position` | Nama posisi seperti tertulis | — |
| `company` | Perusahaan yang merekrut | disamarkan/tidak disebut → `null` |
| `location` | Kota/negara penempatan atau "Remote" | tidak disebut → `null` |
| `required_skills` | Skill yang diminta di kualifikasi atau tanggung jawab: bahasa pemrograman, tools, software, metode, bidang keahlian, soft skill yang disebut eksplisit. Satu skill per item, ditulis seperti di teks, gabungan dipisah ("Python/R" → `"Python"`, `"R"`) | `[]` |
| `preferred_skills` | Skill bertanda plus, preferred, nice to have, diutamakan, nilai tambah | `[]` |
| `education_level` | Jenjang minimal: `sma`, `d3`, `d4`, `s1`, `s2`, `s3`. Bila beberapa diterima (D3/S1), pilih yang terendah | `null` |
| `education_fields` | Jurusan yang disebut, seperti tertulis | semua jurusan/tidak disebut → `[]` |
| `min_experience_years` | Angka tahun minimal (6 bulan = `0.5`). `0` bila fresh graduate dipersilakan tanpa syarat pengalaman | tidak disebut → `null` |
| `responsibilities` | Butir tanggung jawab, disalin apa adanya | `[]` |

Yang **bukan** skill: usia, domisili, SIM, kesediaan ditempatkan, status kesehatan.

## Cara menilai

- Field tunggal: akurasi, cocok bila sama setelah huruf kecil, spasi, dan tanda baca diabaikan. Angka harus sama persis.
- Field daftar: F1 mikro atas semua lowongan (tiap item label hanya bisa dipasangkan sekali). `responsibilities` boleh sedikit beda redaksi (kemiripan ≥ 85%). Kedua sisi kosong dihitung benar.
- Lowongan yang gagal diekstrak dicatat terpisah dan tidak masuk skor.
