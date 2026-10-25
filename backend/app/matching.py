"""Skor kecocokan profil dengan lowongan (PRD 7.3), dihitung deterministik tanpa LLM.

Empat kategori: skill wajib, skill nilai tambah, pendidikan, dan pengalaman. Kategori
yang tidak disyaratkan lowongan tidak dihitung, dan bobotnya dibagi ke kategori lain.
Setiap kecocokan menyimpan ID entri/butir profil sebagai bukti (dipakai lagi di Fase 4).
"""

import re
from dataclasses import dataclass, field
from datetime import date

SCORER_VERSION = "match-v1"

DEFAULT_WEIGHTS = {"required_skills": 50, "preferred_skills": 10, "education": 15, "experience": 25}

EDUCATION_RANK = {"sma": 0, "d3": 1, "d4": 2, "s1": 3, "s2": 4, "s3": 5}
# Porsi syarat jenjang dalam skor pendidikan bila lowongan juga menyebut jurusan.
EDUCATION_LEVEL_SHARE = 0.7

# Jenjang dari teks entri pendidikan, dicek dari yang tertinggi. Singkatan gelar
# wajib bertitik ("S.Kom", "M.T") supaya tidak tertukar dengan kata biasa ("se", "mt").
EDUCATION_PATTERNS = [
    ("s3", r"\b(s-?3|doktor|doctor(al)?|ph\.\s?d)\b"),
    ("s2", r"\b(s-?2|magister|master|m\.\s?(sc|kom|t|m|si|b\.a))\b"),
    ("d4", r"\b(d-?4|d-?iv|diploma\s?(iv|4)|sarjana terapan|s\.\s?tr)\b"),
    ("s1", r"\b(s-?1|sarjana|bachelor|undergraduate|b\.\s?(sc|a|eng)"
           r"|s\.\s?(kom|t|e|si|psi|h|ked|pd|ak))\b"),
    ("d3", r"\b(d-?3|d-?iii|diploma|a\.\s?md)\b"),
    ("sma", r"\b(sma|smk|slta|high school)\b"),
]  # fmt: skip

# Nama bahasa yang sering ditulis berbeda di CV dan lowongan.
LANGUAGE_ALIASES = [
    {"english", "inggris", "bahasa inggris"},
    {"indonesian", "indonesia", "bahasa indonesia"},
    {"mandarin", "chinese", "bahasa mandarin"},
    {"japanese", "jepang", "bahasa jepang"},
    {"korean", "korea", "bahasa korea"},
    {"arabic", "arab", "bahasa arab"},
    {"german", "jerman", "bahasa jerman"},
]

# Skill sependek ini ("R", "C", "Go") terlalu mudah muncul tanpa sengaja di kalimat,
# jadi hanya dicocokkan dengan judul entri, tidak dengan butir pengalaman.
SHORT_SKILL_LEN = 2

# Urutan bukti: entri skill paling langsung, butir pengalaman paling tidak langsung.
SECTION_ORDER = ["skill", "certification", "language", "experience", "project", "organization",
                 "education"]  # fmt: skip
MAX_EVIDENCE = 3


# --- Data masukan -------------------------------------------------------------


@dataclass
class Bullet:
    id: str
    text: str


@dataclass
class ProfileEntry:
    id: str
    section: str
    title: str
    organization: str | None = None
    start_month: date | None = None
    end_month: date | None = None
    is_current: bool = False
    description: str | None = None
    bullets: list[Bullet] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: dict) -> "ProfileEntry":
        """Dari baris Supabase `profile_entries` dengan `profile_bullets(id, position, text)`."""
        bullets = sorted(row.get("profile_bullets") or [], key=lambda b: b.get("position", 0))
        return cls(
            id=row["id"],
            section=row["section"],
            title=row["title"],
            organization=row.get("organization"),
            start_month=_date(row.get("start_month")),
            end_month=_date(row.get("end_month")),
            is_current=bool(row.get("is_current")),
            description=row.get("description"),
            bullets=[Bullet(b["id"], b["text"]) for b in bullets],
        )


def _date(value) -> date | None:
    if value is None or isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


@dataclass
class Job:
    required_skills: list[str]
    preferred_skills: list[str]
    education_level: str | None
    education_fields: list[str]
    min_experience_years: float | None

    @classmethod
    def from_row(cls, row: dict) -> "Job":
        years = row.get("min_experience_years")
        return cls(
            required_skills=list(row.get("required_skills") or []),
            preferred_skills=list(row.get("preferred_skills") or []),
            education_level=row.get("education_level"),
            education_fields=list(row.get("education_fields") or []),
            min_experience_years=None if years is None else float(years),
        )


# --- Normalisasi teks -----------------------------------------------------------


def norm(text: str) -> str:
    """Huruf kecil, tanda baca jadi spasi (kecuali + dan #, untuk C++ dan C#)."""
    return " ".join(re.sub(r"[^\w+#]+", " ", text.casefold()).split())


def _contains(phrase: str, text: str) -> bool:
    """True bila `phrase` muncul utuh per kata di `text` (keduanya sudah dinormalisasi)."""
    return bool(phrase) and f" {phrase} " in f" {text} "


def _variants(skill: str) -> set[str]:
    """Nama skill, tanpa isi kurung, dan isi kurungnya: "Large Language Models (LLM)"."""
    found = {norm(skill), norm(re.sub(r"\([^)]*\)", " ", skill))}
    found |= {norm(inner) for inner in re.findall(r"\(([^)]*)\)", skill)}
    for group in LANGUAGE_ALIASES:
        if found & group:
            found |= group
    return {v for v in found if v}


def _acronym(text: str) -> str:
    """Singkatan minimal tiga huruf ("uat"); dua huruf terlalu ambigu (AI = Adobe Illustrator?)."""
    words = text.split()
    return "".join(w[0] for w in words) if len(words) >= 3 else ""


# --- Skill --------------------------------------------------------------------


@dataclass
class Evidence:
    entry_id: str
    bullet_id: str | None = None


@dataclass
class SkillMatch:
    skill: str
    matched: bool
    method: str | None = None  # "exact" (judul entri) atau "text" (muncul di teks profil)
    evidence: list[Evidence] = field(default_factory=list)


def _sorted_entries(entries: list[ProfileEntry]) -> list[ProfileEntry]:
    rank = {s: i for i, s in enumerate(SECTION_ORDER)}
    return sorted(entries, key=lambda e: rank.get(e.section, len(rank)))


def match_skill(skill: str, entries: list[ProfileEntry]) -> SkillMatch:
    variants = _variants(skill)
    exact, text = [], []
    for entry in _sorted_entries(entries):
        title_variants = _variants(entry.title)
        if variants & title_variants or any(
            v == _acronym(t) or t == _acronym(v) for v in variants for t in title_variants
        ):
            exact.append(Evidence(entry.id))
            continue
        searchable = [v for v in variants if len(v) > SHORT_SKILL_LEN]
        if not searchable:
            continue
        header = norm(f"{entry.title} {entry.description or ''}")
        if any(_contains(v, header) for v in searchable):
            text.append(Evidence(entry.id))
            continue
        for bullet in entry.bullets:
            if any(_contains(v, norm(bullet.text)) for v in searchable):
                text.append(Evidence(entry.id, bullet.id))
    if exact:
        return SkillMatch(skill, True, "exact", (exact + text)[:MAX_EVIDENCE])
    if text:
        return SkillMatch(skill, True, "text", text[:MAX_EVIDENCE])
    return SkillMatch(skill, False)


def match_skills(skills: list[str], entries: list[ProfileEntry]) -> list[SkillMatch]:
    seen, result = set(), []
    for skill in skills:
        key = norm(skill)
        if key and key not in seen:
            seen.add(key)
            result.append(match_skill(skill, entries))
    return result


# --- Pendidikan -----------------------------------------------------------------


def education_level_of(entry: ProfileEntry) -> str | None:
    text = f"{entry.title} {entry.description or ''}"
    for level, pattern in EDUCATION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return level
    return None


@dataclass
class EducationMatch:
    required_level: str | None
    profile_level: str | None
    level_met: bool
    level_evidence: list[Evidence]
    required_fields: list[str]
    field_matched: str | None
    field_evidence: list[Evidence]


def match_education(job: Job, entries: list[ProfileEntry]) -> EducationMatch:
    education = [e for e in entries if e.section == "education"]

    best, best_entries = None, []
    for entry in education:
        level = education_level_of(entry)
        if level is None:
            continue
        if best is None or EDUCATION_RANK[level] > EDUCATION_RANK[best]:
            best, best_entries = level, [entry]
        elif level == best:
            best_entries.append(entry)
    level_met = (
        job.education_level is not None
        and best is not None
        and EDUCATION_RANK[best] >= EDUCATION_RANK[job.education_level]
    )

    field_matched, field_evidence = None, []
    for wanted in job.education_fields:
        key = norm(wanted)
        hits = [e for e in education if key and _contains(key, norm(e.title))]
        if hits:
            field_matched, field_evidence = wanted, [Evidence(e.id) for e in hits]
            break

    return EducationMatch(
        required_level=job.education_level,
        profile_level=best,
        level_met=level_met,
        level_evidence=[Evidence(e.id) for e in best_entries],
        required_fields=list(job.education_fields),
        field_matched=field_matched,
        field_evidence=field_evidence,
    )


def education_score(m: EducationMatch) -> float | None:
    has_level, has_fields = m.required_level is not None, bool(m.required_fields)
    if not has_level and not has_fields:
        return None
    level = 1.0 if m.level_met else 0.0
    fields = 1.0 if m.field_matched else 0.0
    if not has_fields:
        return level
    if not has_level:
        return fields
    return EDUCATION_LEVEL_SHARE * level + (1 - EDUCATION_LEVEL_SHARE) * fields


# --- Pengalaman -----------------------------------------------------------------


def _month_index(d: date) -> int:
    return d.year * 12 + d.month - 1


def experience_months(entries: list[ProfileEntry], today: date) -> tuple[int, list[Evidence]]:
    """Total bulan pengalaman kerja; bulan yang tumpang tindih hanya dihitung sekali.

    Entri tanpa tanggal mulai tidak bisa dihitung. Entri tanpa tanggal selesai dan tidak
    sedang berjalan dihitung satu bulan. Bulan selesai ikut dihitung (Jan-Mar = 3 bulan).
    """
    months: set[int] = set()
    evidence = []
    for entry in entries:
        if entry.section != "experience" or entry.start_month is None:
            continue
        start = _month_index(entry.start_month)
        if entry.is_current:
            end = _month_index(today)
        elif entry.end_month is not None:
            end = _month_index(entry.end_month)
        else:
            end = start
        if end < start:
            continue
        months.update(range(start, end + 1))
        evidence.append(Evidence(entry.id))
    return len(months), evidence


@dataclass
class ExperienceMatch:
    required_years: float | None
    profile_years: float
    evidence: list[Evidence]


def match_experience(job: Job, entries: list[ProfileEntry], today: date) -> ExperienceMatch:
    months, evidence = experience_months(entries, today)
    return ExperienceMatch(job.min_experience_years, round(months / 12, 1), evidence)


def experience_score(m: ExperienceMatch) -> float | None:
    if m.required_years is None:
        return None
    if m.required_years <= 0:
        return 1.0
    return min(1.0, m.profile_years / m.required_years)


# --- Skor total -----------------------------------------------------------------


@dataclass
class Category:
    weight: float
    score: float | None  # 0-1; None bila lowongan tidak mensyaratkan kategori ini
    detail: object


@dataclass
class MatchResult:
    score: int | None  # 0-100; None bila lowongan tidak mensyaratkan apa pun
    categories: dict[str, Category]
    scorer_version: str = SCORER_VERSION


def _skill_score(matches: list[SkillMatch]) -> float | None:
    if not matches:
        return None
    return sum(m.matched for m in matches) / len(matches)


def validate_weights(weights: dict[str, float]) -> dict[str, float]:
    if set(weights) != set(DEFAULT_WEIGHTS):
        raise ValueError(f"Bobot harus berisi tepat: {', '.join(DEFAULT_WEIGHTS)}")
    if any(w < 0 for w in weights.values()) or sum(weights.values()) <= 0:
        raise ValueError("Bobot tidak boleh negatif dan totalnya harus lebih dari 0")
    return dict(weights)


def match(
    job: Job,
    entries: list[ProfileEntry],
    today: date,
    weights: dict[str, float] | None = None,
) -> MatchResult:
    weights = validate_weights(weights or DEFAULT_WEIGHTS)
    required = match_skills(job.required_skills, entries)
    preferred = match_skills(job.preferred_skills, entries)
    education = match_education(job, entries)
    experience = match_experience(job, entries, today)

    categories = {
        "required_skills": Category(weights["required_skills"], _skill_score(required), required),
        "preferred_skills": Category(
            weights["preferred_skills"], _skill_score(preferred), preferred
        ),
        "education": Category(weights["education"], education_score(education), education),
        "experience": Category(weights["experience"], experience_score(experience), experience),
    }
    counted = [c for c in categories.values() if c.score is not None and c.weight > 0]
    total_weight = sum(c.weight for c in counted)
    if not total_weight:
        return MatchResult(None, categories)
    # Dibulatkan ke bilangan bulat supaya selisih pecahan tidak terlihat sebagai beda skor.
    score = round(100 * sum(c.weight * c.score for c in counted) / total_weight)
    return MatchResult(score, categories)


def gaps(result: MatchResult) -> dict[str, list[str]]:
    """Skill yang diminta tetapi tidak ditemukan di profil (PRD US-4)."""
    return {
        name: [m.skill for m in result.categories[name].detail if not m.matched]
        for name in ("required_skills", "preferred_skills")
    }
