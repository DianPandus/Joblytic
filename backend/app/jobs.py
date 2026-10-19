"""Ekstraksi persyaratan lowongan ke skema terstruktur (PRD 7.2).

Alur: normalisasi teks -> LLM mengisi skema Pydantic (diulang sekali dengan prompt
lebih ketat bila gagal) -> buang isian yang tidak bisa ditemukan di teks lowongan.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from app.grounding import clean, supported, words
from app.llm import LLMClient, LLMError

PROMPT_VERSION = "job-extract-v1"
MIN_TEXT_CHARS = 80
MAX_TEXT_CHARS = 20_000

EducationLevel = Literal["sma", "d3", "d4", "s1", "s2", "s3"]


class JobError(Exception):
    """Masalah pada teks lowongan yang perlu diperbaiki pengguna (pesan aman ditampilkan)."""


# --- Skema keluaran LLM -------------------------------------------------------


class JobExtraction(BaseModel):
    position: str | None = Field(description="Nama posisi/jabatan. null jika tidak tertulis.")
    company: str | None = Field(
        description="Nama perusahaan yang merekrut. null jika tidak tertulis (mis. disamarkan)."
    )
    location: str | None = Field(
        description="Kota/negara penempatan, atau Remote. null jika tidak tertulis."
    )
    required_skills: list[str] = Field(
        description="Skill wajib: bahasa pemrograman, tools, software, metode, bidang keahlian, "
        "dan soft skill yang disebut eksplisit. Satu skill per item, singkat (1-4 kata), "
        "disalin seperti tertulis."
    )
    preferred_skills: list[str] = Field(
        description="Skill yang ditandai nilai tambah: plus, preferred, nice to have, "
        "diutamakan, lebih disukai, menjadi nilai tambah. Format sama dengan required_skills."
    )
    education_level: EducationLevel | None = Field(
        description="Jenjang pendidikan minimal: sma (SMA/SMK), d3, d4, s1 (sarjana/bachelor), "
        "s2 (magister/master), s3 (doktor/PhD). Jika beberapa jenjang diterima, pilih yang "
        "terendah. null jika tidak tertulis."
    )
    education_fields: list[str] = Field(
        description="Jurusan/bidang studi yang diminta, disalin seperti tertulis. "
        "Kosongkan jika tidak disebut atau semua jurusan."
    )
    min_experience_years: float | None = Field(
        description="Pengalaman kerja minimal dalam tahun (6 bulan = 0.5). 0 jika tertulis "
        "fresh graduate dipersilakan tanpa syarat pengalaman. null jika tidak tertulis."
    )
    responsibilities: list[str] = Field(
        description="Tanggung jawab/deskripsi pekerjaan utama, satu butir per item, "
        "disalin apa adanya. Kosongkan jika tidak ada."
    )


SYSTEM_PROMPT = """Kamu mengekstrak persyaratan dari teks lowongan kerja ke data terstruktur.
Aturan:
- Hanya ambil informasi yang benar-benar tertulis di teks. Jangan menebak, menyimpulkan
  dari nama posisi, menerjemahkan, atau menambah apa pun.
- Field yang tidak tertulis diisi null (atau list kosong).
- Salin teks dalam bahasa aslinya.
- Pisahkan skill gabungan menjadi item sendiri ("Python/R" -> "Python", "R";
  "Excel dan Power BI" -> "Excel", "Power BI").
- Skill yang sama jangan diulang, dan jangan masuk ke required_skills sekaligus
  preferred_skills.
- Persyaratan umum non-skill (usia, domisili, bersedia ditempatkan, SIM) bukan skill."""

STRICT_SUFFIX = """
PENTING: percobaan sebelumnya tidak valid. Keluarkan JSON yang persis mengikuti skema;
education_level hanya salah satu dari sma, d3, d4, s1, s2, s3, atau null."""


# --- Normalisasi teks & cache key ---------------------------------------------


def normalize_text(text: str) -> str:
    """Rapikan spasi tanpa mengubah isi, supaya tempelan yang sama menghasilkan hash sama."""
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def validate_text(text: str) -> str:
    text = normalize_text(text)
    if len(text) < MIN_TEXT_CHARS:
        raise JobError("Teks lowongan terlalu pendek. Tempel deskripsi lowongan selengkapnya.")
    if len(text) > MAX_TEXT_CHARS:
        raise JobError(f"Teks lowongan maksimal {MAX_TEXT_CHARS:,} karakter.".replace(",", "."))
    return text


def text_hash(normalized_text: str) -> str:
    return hashlib.sha256(normalized_text.casefold().encode("utf-8")).hexdigest()


# --- Grounding ----------------------------------------------------------------

# Penanda jenjang pendidikan; jenjang hanya dipercaya bila teks memang menyebut
# pendidikan, karena nilainya hasil pemetaan dan tidak bisa dicocokkan kata per kata.
EDUCATION_RE = re.compile(
    r"\b(sma|smk|slta|d-?[34]|diploma|s-?[123]|sarjana|bachelor|magister|master|doktor"
    r"|doctoral|ph\.?d|pendidikan|education|degree|graduate|lulusan)\b",
    re.IGNORECASE,
)
FRESH_RE = re.compile(r"fresh\s*grad|lulusan baru|tanpa pengalaman|no experience", re.IGNORECASE)
NUMBER_WORDS = {
    1: ("satu", "one", "setahun"),
    2: ("dua", "two"),
    3: ("tiga", "three"),
    4: ("empat", "four"),
    5: ("lima", "five"),
    6: ("enam", "six"),
    7: ("tujuh", "seven"),
    8: ("delapan", "eight"),
    9: ("sembilan", "nine"),
    10: ("sepuluh", "ten"),
}


def _years_supported(years: float, text: str) -> bool:
    if years == 0:
        return bool(FRESH_RE.search(text))
    if years < 1:  # dalam bulan, mis. "6 bulan"
        return bool(re.search(rf"\b{round(years * 12)}\s*(bulan|months?)\b", text, re.I))
    number = f"{years:g}"
    pattern = re.escape(number).replace(r"\.", r"[.,]")
    if re.search(rf"(?<![\d.,]){pattern}(?![\d])", text):
        return True
    names = NUMBER_WORDS.get(int(years), ()) if years.is_integer() else ()
    return any(re.search(rf"\b{n}\b", text, re.IGNORECASE) for n in names)


def _keep_list(items: list[str], source_words: set[str], limit: int, max_len: int):
    kept, seen, dropped = [], set(), 0
    for item in items:
        value = clean(item, max_len)
        if not value:
            continue
        if not supported(value, source_words):
            dropped += 1
            continue
        key = value.casefold()
        if key not in seen and len(kept) < limit:
            seen.add(key)
            kept.append(value)
    return kept, dropped


@dataclass
class JobResult:
    fields: dict
    dropped: int


def ground(extraction: JobExtraction, source_text: str) -> JobResult:
    source_words = set(words(source_text))
    dropped = 0

    def keep(value: str | None, limit: int) -> str | None:
        nonlocal dropped
        value = clean(value, limit)
        if value and not supported(value, source_words):
            dropped += 1
            return None
        return value

    required, d1 = _keep_list(extraction.required_skills, source_words, 60, 100)
    preferred, d2 = _keep_list(extraction.preferred_skills, source_words, 60, 100)
    required_keys = {s.casefold() for s in required}
    preferred = [s for s in preferred if s.casefold() not in required_keys]
    fields_of_study, d3 = _keep_list(extraction.education_fields, source_words, 30, 200)
    responsibilities, d4 = _keep_list(extraction.responsibilities, source_words, 40, 1000)
    dropped += d1 + d2 + d3 + d4

    level = extraction.education_level
    if level and not EDUCATION_RE.search(source_text):
        level, dropped = None, dropped + 1

    years = extraction.min_experience_years
    if years is not None:
        years = round(years * 2) / 2  # kolom numeric(4,1); setengah tahun sudah cukup teliti
        if not (0 <= years <= 50) or not _years_supported(years, source_text):
            years, dropped = None, dropped + 1

    position = keep(extraction.position, 200)
    company = keep(extraction.company, 200)
    location = keep(extraction.location, 200)
    return JobResult(
        fields={
            "position": position,
            "company": company,
            "location": location,
            "required_skills": required,
            "preferred_skills": preferred,
            "education_level": level,
            "education_fields": fields_of_study,
            "min_experience_years": years,
            "responsibilities": responsibilities,
        },
        dropped=dropped,
    )


async def extract_job(llm: LLMClient, text: str) -> JobResult:
    """Panggil LLM (maksimal dua kali, kedua dengan instruksi lebih ketat), lalu grounding."""
    prompt = f"Teks lowongan:\n<<<\n{text}\n>>>"
    last_error: LLMError | None = None
    for system in (SYSTEM_PROMPT, SYSTEM_PROMPT + STRICT_SUFFIX):
        try:
            extraction = await llm.generate_json(system, prompt, JobExtraction)
            return ground(extraction, text)
        except LLMError as exc:
            if exc.__class__ is not LLMError:  # kuota/konfigurasi: jangan diulang
                raise
            last_error = exc
    assert last_error is not None
    raise last_error
