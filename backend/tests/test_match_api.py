import httpx
import pytest

from app import match_api
from tests.helpers import bearer, make_token

JOB_ID = "22222222-2222-2222-2222-222222222222"

JOB_ROW = {
    "id": JOB_ID,
    "required_skills": ["SQL", "Python"],
    "preferred_skills": ["dbt"],
    "education_level": "s1",
    "education_fields": [],
    "min_experience_years": 0,
}

PROFILE_ROWS = [
    {
        "id": "exp",
        "section": "experience",
        "title": "Data Analyst Intern",
        "start_month": "2025-01-01",
        "end_month": "2025-06-01",
        "is_current": False,
        "profile_bullets": [{"id": "b1", "position": 0, "text": "Menulis query SQL harian"}],
    },
    {"id": "edu", "section": "education", "title": "S1 Statistika", "profile_bullets": []},
    {"id": "unused", "section": "skill", "title": "Figma", "profile_bullets": []},
]


@pytest.fixture
def match_client(client, monkeypatch):
    state = {"jobs": [JOB_ROW], "profile": PROFILE_ROWS, "upserted": None, "db_down": False}

    async def select_rows(user, s, table, params):
        if state["db_down"]:
            raise httpx.ConnectError("down")
        return state["jobs"] if table == "job_postings" else state["profile"]

    async def upsert_row(user, s, table, row, on_conflict):
        assert table == "job_matches" and on_conflict == "job_posting_id"
        state["upserted"] = row

    monkeypatch.setattr(match_api.supabase, "select_rows", select_rows)
    monkeypatch.setattr(match_api.supabase, "upsert_row", upsert_row)
    client.state = state
    return client


def post_match(client, job_id=JOB_ID):
    return client.post(f"/jobs/{job_id}/match", headers=bearer(make_token()))


def test_match_returns_score_gaps_and_cited_sources(match_client):
    resp = post_match(match_client)
    assert resp.status_code == 200
    data = resp.json()
    # skill wajib 1/2, nilai tambah 0/1, pendidikan 1, pengalaman 1 (fresh graduate)
    assert data["score"] == round((50 * 0.5 + 15 + 25) / 100 * 100)
    assert data["gaps"] == {"required_skills": ["Python"], "preferred_skills": ["dbt"]}
    assert set(data["sources"]["entries"]) == {"exp", "edu"}
    assert data["sources"]["bullets"] == {"b1": "Menulis query SQL harian"}
    assert data["profile_entries"] == 3

    row = match_client.state["upserted"]
    assert row["job_posting_id"] == JOB_ID and row["score"] == data["score"]
    assert row["scorer_version"] == "match-v1" and row["result"]["gaps"] == data["gaps"]


def test_match_unknown_job_is_404(match_client):
    match_client.state["jobs"] = []
    assert post_match(match_client).status_code == 404
    assert match_client.state["upserted"] is None


def test_match_rejects_invalid_id_and_reports_db_failure(match_client):
    assert post_match(match_client, job_id="bukan-uuid").status_code == 422
    match_client.state["db_down"] = True
    assert post_match(match_client).status_code == 503


def test_match_requires_login(match_client):
    assert match_client.post(f"/jobs/{JOB_ID}/match").status_code == 401
