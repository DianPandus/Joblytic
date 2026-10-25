from datetime import date

import pytest

from app.matching import (
    Bullet,
    Job,
    ProfileEntry,
    education_level_of,
    experience_months,
    gaps,
    match,
    match_skill,
)

TODAY = date(2026, 10, 1)


def entry(section, title, id=None, **kw) -> ProfileEntry:
    return ProfileEntry(id=id or f"{section}:{title}", section=section, title=title, **kw)


def job(**overrides) -> Job:
    base = {
        "required_skills": ["SQL", "Python"],
        "preferred_skills": ["dbt"],
        "education_level": "s1",
        "education_fields": ["Statistika", "Informatika"],
        "min_experience_years": 1,
    }
    return Job(**{**base, **overrides})


PROFILE = [
    entry("education", "S1 Teknik Informatika", id="edu"),
    entry(
        "experience",
        "Data Analyst Intern",
        id="exp",
        start_month=date(2025, 1, 1),
        end_month=date(2025, 6, 1),
        bullets=[Bullet("b1", "Membuat query SQL untuk laporan penjualan")],
    ),
    entry("skill", "Python", id="py"),
]


# --- Skill --------------------------------------------------------------------


def test_skill_matches_entry_title_before_bullet_text():
    m = match_skill("python", PROFILE)
    assert m.matched and m.method == "exact" and m.evidence[0].entry_id == "py"
    m = match_skill("SQL", PROFILE)
    assert m.matched and m.method == "text"
    assert (m.evidence[0].entry_id, m.evidence[0].bullet_id) == ("exp", "b1")


def test_skill_text_match_needs_whole_words():
    profile = [entry("project", "Dashboard", bullets=[Bullet("b", "Pakai MySQL dan JavaScript")])]
    assert not match_skill("SQL", profile).matched
    assert not match_skill("Java", profile).matched
    assert match_skill("MySQL", profile).matched


def test_short_skills_only_match_titles():
    profile = [entry("experience", "Riset", bullets=[Bullet("b", "Koordinasi tim R&D")])]
    assert not match_skill("R", profile).matched
    assert match_skill("R", [entry("skill", "R")]).matched


def test_skill_variants_parentheses_acronyms_and_languages():
    assert match_skill("LLM", [entry("skill", "Large Language Models (LLM)")]).matched
    assert match_skill("User Acceptance Testing", [entry("skill", "UAT")]).matched
    assert not match_skill("AI", [entry("skill", "Adobe Illustrator")]).matched
    assert match_skill("English", [entry("language", "Bahasa Inggris")]).matched
    assert match_skill("Excel", [entry("skill", "Microsoft Excel")]).method == "text"


# --- Pendidikan & pengalaman ----------------------------------------------------


@pytest.mark.parametrize(
    "title, level",
    [
        ("S1 Teknik Informatika", "s1"),
        ("Sarjana Komputer (S.Kom)", "s1"),
        ("Bachelor of Computer Science", "s1"),
        ("D3 Manajemen Informatika", "d3"),
        ("Diploma IV Akuntansi", "d4"),
        ("Magister Manajemen", "s2"),
        ("SMK Negeri 1 Jakarta", "sma"),
        ("Universitas Indonesia", None),
    ],
)
def test_education_level_from_entry_text(title, level):
    assert education_level_of(entry("education", title)) == level


def test_experience_counts_overlapping_months_once():
    entries = [
        entry("experience", "A", start_month=date(2025, 1, 1), end_month=date(2025, 6, 1)),
        entry("experience", "B", start_month=date(2025, 4, 1), end_month=date(2025, 9, 1)),
        entry("experience", "C", start_month=date(2026, 7, 1), is_current=True),
        entry("experience", "Tanpa tanggal"),
        entry("organization", "Himpunan", start_month=date(2020, 1, 1), end_month=date(2022, 1, 1)),
    ]
    months, evidence = experience_months(entries, TODAY)
    assert months == 9 + 4
    assert [e.entry_id for e in evidence] == ["experience:A", "experience:B", "experience:C"]


# --- Skor total -----------------------------------------------------------------


def test_match_scores_each_category():
    result = match(job(), PROFILE, TODAY)
    c = result.categories
    assert c["required_skills"].score == 1.0
    assert c["preferred_skills"].score == 0.0
    assert c["education"].score == 1.0
    assert c["experience"].score == 0.5
    # (50*1 + 10*0 + 15*1 + 25*0.5) / 100
    assert result.score == 78
    assert gaps(result) == {"required_skills": [], "preferred_skills": ["dbt"]}


def test_unrequired_categories_drop_out_and_weights_are_redistributed():
    result = match(
        job(preferred_skills=[], education_level=None, education_fields=[],
            min_experience_years=None),
        PROFILE,
        TODAY,
    )  # fmt: skip
    assert result.categories["education"].score is None
    assert result.score == 100
    assert match(Job([], [], None, [], None), PROFILE, TODAY).score is None


def test_education_level_without_matching_field_gets_partial_score():
    result = match(job(education_fields=["Akuntansi"]), PROFILE, TODAY)
    assert result.categories["education"].score == pytest.approx(0.7)


def test_fresh_graduate_posting_gives_full_experience_score():
    assert match(job(min_experience_years=0), [], TODAY).categories["experience"].score == 1.0


def test_custom_weights_and_validation():
    weights = {"required_skills": 0, "preferred_skills": 1, "education": 0, "experience": 0}
    assert match(job(), PROFILE, TODAY, weights).score == 0
    with pytest.raises(ValueError):
        match(job(), PROFILE, TODAY, {"required_skills": 1})
    with pytest.raises(ValueError):
        match(job(), PROFILE, TODAY, {**weights, "education": -1})


def test_same_input_gives_same_result():
    assert match(job(), PROFILE, TODAY) == match(job(), PROFILE, TODAY)


def test_profile_entry_from_supabase_row():
    row = {
        "id": "e1",
        "section": "experience",
        "title": "Intern",
        "start_month": "2025-01-01",
        "end_month": None,
        "is_current": True,
        "profile_bullets": [
            {"id": "b2", "position": 1, "text": "Kedua"},
            {"id": "b1", "position": 0, "text": "Pertama"},
        ],
    }
    e = ProfileEntry.from_row(row)
    assert e.start_month == date(2025, 1, 1) and e.is_current
    assert [b.id for b in e.bullets] == ["b1", "b2"]
