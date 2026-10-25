from evals.job_extraction import f1, list_counts, scalar_match, score


def label(**overrides) -> dict:
    base = {
        "position": "Data Analyst",
        "company": "PT Contoh",
        "location": "Jakarta",
        "education_level": "s1",
        "min_experience_years": 1,
        "required_skills": ["SQL", "Python"],
        "preferred_skills": [],
        "education_fields": ["Statistika"],
        "responsibilities": ["Membuat dashboard penjualan mingguan"],
    }
    return {**base, **overrides}


def test_scalar_match_ignores_case_spacing_and_punctuation():
    assert scalar_match("data  analyst.", "Data Analyst")
    assert scalar_match(1.0, 1) and not scalar_match(2, 1)
    assert scalar_match(None, None) and not scalar_match(None, "Jakarta")


def test_list_counts_pairs_each_label_once_and_fuzzy_only_when_asked():
    assert list_counts(["SQL", "sql", "Excel"], ["SQL", "Python"], fuzzy=False) == (1, 3, 2)
    pred = ["Membuat dashboard penjualan mingguan."]
    assert list_counts(pred, ["membuat dashboard penjualan mingguan"], fuzzy=True)[0] == 1
    assert list_counts(["Power BI"], ["Tableau"], fuzzy=True)[0] == 0


def test_fuzzy_skill_match_ignores_filler_words_only():
    assert list_counts(["Good analytical skills"], ["analytical"], fuzzy=True)[0] == 1
    assert list_counts(["Fluent English"], ["English"], fuzzy=True)[0] == 1
    assert list_counts(["SQL"], ["MySQL"], fuzzy=True)[0] == 0
    assert list_counts(["Java"], ["JavaScript"], fuzzy=True)[0] == 0
    assert list_counts(["Visual Basic"], ["Visual"], fuzzy=True)[0] == 0
    assert list_counts(["UAT"], ["User Acceptance Testing"], fuzzy=True)[0] == 1
    assert list_counts(["SQL"], ["Structured Data"], fuzzy=True)[0] == 0
    assert list_counts(["Good analytical skills"], ["analytical"], fuzzy=False)[0] == 0


def test_f1_treats_both_empty_as_correct():
    assert f1(0, 0, 0) == 1.0
    assert f1(0, 1, 0) == 0.0


def test_score_reports_per_field_and_lists_wrong_postings():
    cases = [
        ("a", label(), label()),
        ("b", label(company=None, required_skills=["SQL"]), label()),
    ]
    report = score(cases)
    assert report["position"]["score"] == 1.0
    assert report["company"]["score"] == 0.5 and report["company"]["errors"] == ["b"]
    assert report["required_skills"]["precision"] == 1.0
    assert report["required_skills"]["recall"] == 0.75
    assert report["preferred_skills"]["score"] == 1.0
