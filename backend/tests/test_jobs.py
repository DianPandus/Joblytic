import httpx
import pytest

from app import jobs_api
from app.jobs import (
    JobError,
    JobExtraction,
    extract_job,
    ground,
    normalize_text,
    text_hash,
    validate_text,
)
from app.llm import LLMError, LLMQuotaError
from tests.helpers import FakeLLM, bearer, make_token

JOB_TEXT = """Data Analyst - PT Contoh Digital
Lokasi: Jakarta Selatan (Hybrid)

Tanggung jawab:
- Membuat dashboard penjualan mingguan
- Menganalisis data pelanggan untuk tim marketing

Kualifikasi:
- Minimal S1 Statistika, Matematika, atau Teknik Informatika
- Pengalaman minimal 1 tahun, fresh graduate dipersilakan melamar
- Menguasai SQL dan Python
- Familiar dengan Power BI atau Tableau
- Pengalaman dengan dbt menjadi nilai tambah"""


def extraction(**overrides) -> JobExtraction:
    base = {
        "position": "Data Analyst",
        "company": "PT Contoh Digital",
        "location": "Jakarta Selatan",
        "required_skills": ["SQL", "Python", "Power BI", "Tableau"],
        "preferred_skills": ["dbt"],
        "education_level": "s1",
        "education_fields": ["Statistika", "Matematika", "Teknik Informatika"],
        "min_experience_years": 1,
        "responsibilities": ["Membuat dashboard penjualan mingguan"],
    }
    return JobExtraction(**{**base, **overrides})


# --- Normalisasi & validasi ---------------------------------------------------


def test_same_posting_with_different_spacing_has_same_hash():
    a = "Data Analyst\n\n\n\nMenguasai   SQL\t dan Python  "
    b = "Data Analyst\n\nmenguasai SQL dan Python"
    assert normalize_text(a) == "Data Analyst\n\nMenguasai SQL dan Python"
    assert text_hash(normalize_text(a)) == text_hash(normalize_text(b))


def test_validate_text_rejects_too_short_and_too_long():
    with pytest.raises(JobError):
        validate_text("Dicari admin")
    with pytest.raises(JobError):
        validate_text("a" * 20_001)
    assert validate_text(JOB_TEXT) == JOB_TEXT


# --- Grounding ----------------------------------------------------------------


def test_ground_keeps_fields_found_in_text():
    result = ground(extraction(), JOB_TEXT)
    assert result.dropped == 0
    assert result.fields["required_skills"] == ["SQL", "Python", "Power BI", "Tableau"]
    assert result.fields["preferred_skills"] == ["dbt"]
    assert result.fields["education_level"] == "s1"
    assert result.fields["min_experience_years"] == 1


def test_ground_drops_invented_values():
    result = ground(
        extraction(
            company="PT Lain Sekali",
            required_skills=["SQL", "Kubernetes", "sql"],
            preferred_skills=["SQL", "Spark"],
            min_experience_years=3,
            responsibilities=["Memimpin tim engineering global"],
        ),
        JOB_TEXT,
    )
    f = result.fields
    assert f["company"] is None
    assert f["required_skills"] == ["SQL"]  # Kubernetes dikarang, "sql" duplikat
    assert f["preferred_skills"] == []  # SQL sudah wajib, Spark dikarang
    assert f["min_experience_years"] is None  # "3" tidak ada di teks
    assert f["responsibilities"] == []
    assert result.dropped == 5


def test_ground_experience_years_from_words_months_and_fresh_graduate():
    text = "Dicari staf admin. Pengalaman minimal dua tahun di bidang administrasi kantor."
    assert ground(extraction(min_experience_years=2), text).fields["min_experience_years"] == 2
    text = "Dicari staf admin dengan pengalaman 6 bulan di bidang administrasi kantor."
    assert ground(extraction(min_experience_years=0.5), text).fields["min_experience_years"] == 0.5
    assert ground(extraction(min_experience_years=0), JOB_TEXT).fields["min_experience_years"] == 0
    text = "Dicari staf admin untuk kantor pusat, pengalaman di bidang administrasi."
    assert ground(extraction(min_experience_years=0), text).fields["min_experience_years"] is None


def test_ground_drops_education_level_when_text_never_mentions_education():
    text = "Dicari barista ramah untuk kedai kopi di Bandung. Shift pagi dan malam bergantian."
    assert ground(extraction(education_level="s1"), text).fields["education_level"] is None


@pytest.mark.anyio
async def test_extract_retries_once_with_stricter_prompt():
    llm = FakeLLM([LLMError("rusak"), extraction()])
    result = await extract_job(llm, JOB_TEXT)
    assert result.fields["position"] == "Data Analyst"
    assert len(llm.systems) == 2 and "PENTING" in llm.systems[1]


@pytest.mark.anyio
async def test_extract_does_not_retry_on_quota():
    llm = FakeLLM([LLMQuotaError("habis"), extraction()])
    with pytest.raises(LLMQuotaError):
        await extract_job(llm, JOB_TEXT)
    assert len(llm.systems) == 1


# --- Endpoint /jobs/extract ---------------------------------------------------


@pytest.fixture
def jobs_client(client, monkeypatch):
    """Fixture `client` (auth palsu, dari conftest) plus Supabase & LLM palsu."""
    state = {"postings": [], "usage": [], "used_today": 0, "inserted": None}

    async def select_rows(user, s, table, params):
        if table == "job_postings":
            return state["postings"]
        assert table == "llm_usage" and params["kind"] == "eq.job_extract"
        return [{"id": i} for i in range(state["used_today"])]

    async def insert_row(user, s, table, row, returning=None):
        if table == "llm_usage":
            state["usage"].append(row)
            return None
        state["inserted"] = row
        return {"id": "posting-1"}

    monkeypatch.setattr(jobs_api.supabase, "select_rows", select_rows)
    monkeypatch.setattr(jobs_api.supabase, "insert_row", insert_row)
    llm = FakeLLM([extraction()])
    monkeypatch.setattr(jobs_api, "get_llm", lambda s: llm)
    client.state = state
    client.llm = llm
    return client


def post_job(client, text=JOB_TEXT, source_url=None):
    return client.post(
        "/jobs/extract",
        headers=bearer(make_token()),
        json={"text": text, "source_url": source_url},
    )


def test_extract_saves_grounded_posting_and_logs_usage(jobs_client):
    resp = post_job(jobs_client, source_url="https://karier.contoh.id/lowongan/1")
    assert resp.status_code == 200
    assert resp.json()["id"] == "posting-1" and resp.json()["cached"] is False

    row = jobs_client.state["inserted"]
    assert row["required_skills"] == ["SQL", "Python", "Power BI", "Tableau"]
    assert row["extracted"]["position"] == "Data Analyst"
    assert row["prompt_version"] == "job-extract-v1" and row["llm_model"] == "fake-model"
    assert len(row["text_hash"]) == 64
    assert [u["status"] for u in jobs_client.state["usage"]] == ["ok"]


def test_extract_returns_cached_posting_without_calling_llm(jobs_client):
    jobs_client.state["postings"] = [{"id": "posting-lama"}]
    resp = post_job(jobs_client)
    assert resp.json() == {"id": "posting-lama", "cached": True}
    assert jobs_client.llm.systems == [] and jobs_client.state["usage"] == []


def test_extract_rejects_short_text_and_bad_url(jobs_client):
    assert post_job(jobs_client, text="Dicari admin").status_code == 422
    resp = post_job(jobs_client, source_url="javascript:alert(1)")
    assert resp.status_code == 422 and "URL" in resp.json()["detail"]


def test_extract_daily_limit(jobs_client):
    jobs_client.state["used_today"] = 20
    resp = post_job(jobs_client)
    assert resp.status_code == 429
    assert jobs_client.llm.systems == []


def test_extract_llm_failure_is_logged(jobs_client, monkeypatch):
    llm = FakeLLM([LLMError("rusak"), LLMError("rusak lagi")])
    monkeypatch.setattr(jobs_api, "get_llm", lambda s: llm)
    resp = post_job(jobs_client)
    assert resp.status_code == 502
    assert jobs_client.state["inserted"] is None
    assert [u["status"] for u in jobs_client.state["usage"]] == ["failed"]


def test_extract_quota_error_is_503(jobs_client, monkeypatch):
    monkeypatch.setattr(jobs_api, "get_llm", lambda s: FakeLLM([LLMQuotaError("habis")]))
    resp = post_job(jobs_client)
    assert resp.status_code == 503 and "Kuota" in resp.json()["detail"]


def test_extract_database_down_is_503(jobs_client, monkeypatch):
    async def down(*args, **kwargs):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(jobs_api.supabase, "select_rows", down)
    assert post_job(jobs_client).status_code == 503
