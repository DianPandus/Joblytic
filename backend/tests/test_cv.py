import io
import zipfile

import pytest

from app import cv_api
from app.cv import (
    DOCX,
    PDF,
    CVError,
    CVExtraction,
    ExtractedEntry,
    detect_type,
    extract_profile,
    ground,
    redact,
)
from app.llm import LLMError, LLMQuotaError
from tests.helpers import bearer, make_token

CV_TEXT = """Budi Santoso
budi@example.com | +62 812-3456-7890 | linkedin.com/in/budi
Jl. Merdeka No. 10, Bandung
PENGALAMAN
Data Analyst Intern - PT Bank Contoh (Jan 2023 - Jun 2023)
- Membangun dashboard Power BI untuk 12 KPI cabang
SKILL
Python, SQL"""


def entry(**overrides) -> ExtractedEntry:
    base = {
        "section": "experience",
        "title": "Data Analyst Intern",
        "organization": "PT Bank Contoh",
        "location": None,
        "start_month": "2023-01",
        "end_month": "2023-06",
        "is_current": False,
        "description": None,
        "bullets": ["Membangun dashboard Power BI untuk 12 KPI cabang"],
    }
    return ExtractedEntry(**{**base, **overrides})


# --- Membaca berkas -----------------------------------------------------------


def make_docx_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
    return buf.getvalue()


def test_detect_type_by_content_not_name():
    assert detect_type(b"%PDF-1.7 ...") == PDF
    assert detect_type(make_docx_bytes()) == DOCX
    with pytest.raises(CVError):
        detect_type(b"MZ\x90\x00 executable")
    with pytest.raises(CVError):
        detect_type(b"PK\x03\x04 not really a zip")


# --- Redaksi identitas --------------------------------------------------------


def test_redact_removes_identity():
    out = redact(CV_TEXT, "Budi Santoso")
    for leaked in ["Budi", "Santoso", "budi@example.com", "812-3456", "linkedin", "Merdeka"]:
        assert leaked.lower() not in out.lower()
    assert "Data Analyst Intern" in out
    assert "2023" in out  # tahun bukan nomor telepon


def test_redact_uses_first_line_when_profile_has_no_name():
    out = redact("Siti Rahma Dewi\nPENDIDIKAN\nUniversitas Indonesia", None)
    assert "Siti" not in out and "Dewi" not in out
    assert "Universitas Indonesia" in out


# --- Grounding ----------------------------------------------------------------


def test_ground_keeps_supported_and_normalizes_dates():
    result = ground(CVExtraction(entries=[entry()]), CV_TEXT)
    assert result.dropped_entries == 0
    e = result.entries[0]
    assert e["start_month"] == "2023-01-01"
    assert e["end_month"] == "2023-06-01"
    assert e["bullets"] == ["Membangun dashboard Power BI untuk 12 KPI cabang"]


def test_ground_drops_invented_entries_and_bullets():
    extraction = CVExtraction(
        entries=[
            entry(bullets=["Memimpin tim 20 engineer membangun platform Kubernetes"]),
            entry(section="skill", title="Kubernetes", organization=None, bullets=[]),
        ]
    )
    result = ground(extraction, CV_TEXT)
    assert result.dropped_entries == 1
    assert result.dropped_bullets == 1
    assert [e["title"] for e in result.entries] == ["Data Analyst Intern"]
    assert result.entries[0]["bullets"] == []


def test_ground_rejects_invalid_or_reversed_dates():
    result = ground(
        CVExtraction(entries=[entry(start_month="2023-13", end_month="2022-01")]), CV_TEXT
    )
    assert result.entries[0]["start_month"] is None
    result = ground(
        CVExtraction(entries=[entry(start_month="2023-06", end_month="2023-01")]), CV_TEXT
    )
    assert result.entries[0]["end_month"] is None


# --- Retry LLM ----------------------------------------------------------------


class FakeLLM:
    model = "fake-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.systems = []

    async def generate_json(self, system, prompt, schema):
        self.systems.append(system)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.anyio
async def test_extract_retries_once_with_stricter_prompt():
    llm = FakeLLM([LLMError("rusak"), CVExtraction(entries=[entry()])])
    result = await extract_profile(llm, CV_TEXT)
    assert len(result.entries) == 1
    assert len(llm.systems) == 2 and "PENTING" in llm.systems[1]


@pytest.mark.anyio
async def test_extract_does_not_retry_on_quota():
    llm = FakeLLM([LLMQuotaError("habis"), CVExtraction(entries=[entry()])])
    with pytest.raises(LLMQuotaError):
        await extract_profile(llm, CV_TEXT)
    assert len(llm.systems) == 1


# --- Endpoint /cv -------------------------------------------------------------


@pytest.fixture
def cv_client(client, monkeypatch):
    """Fixture `client` (auth palsu, dari conftest) plus Supabase & LLM palsu."""
    calls = {"uploads_today": 0, "saved": None, "updates": []}

    async def count(user, s, since):
        return calls["uploads_today"]

    async def upload(user, s, path, data, mime):
        calls["path"] = path

    async def insert(user, s, row):
        calls["row"] = row
        return "upload-1"

    async def update(user, s, upload_id, fields):
        calls["updates"].append(fields)

    async def replace(user, s, entries):
        calls["saved"] = entries
        return len(entries)

    for name, fn in [
        ("count_cv_uploads_since", count),
        ("upload_cv_file", upload),
        ("insert_cv_upload", insert),
        ("update_cv_upload", update),
        ("replace_profile_from_cv", replace),
    ]:
        monkeypatch.setattr(cv_api.supabase, name, fn)

    monkeypatch.setattr(cv_api, "extract_text", lambda data, mime: CV_TEXT)
    llm = FakeLLM([CVExtraction(entries=[entry()])])
    monkeypatch.setattr(cv_api, "get_llm", lambda s: llm)
    client.calls = calls
    return client


def post_cv(client, data=b"%PDF-1.7 fake", consent="true"):
    return client.post(
        "/cv",
        headers=bearer(make_token()),
        files={"file": ("cv.pdf", data, "application/pdf")},
        data={"consent": consent},
    )


def test_cv_requires_consent(cv_client):
    resp = post_cv(cv_client, consent="false")
    assert resp.status_code == 400
    assert cv_client.calls["saved"] is None


def test_cv_rejects_non_cv_file(cv_client):
    resp = post_cv(cv_client, data=b"MZ\x90\x00")
    assert resp.status_code == 422


def test_cv_rejects_large_file(cv_client):
    resp = post_cv(cv_client, data=b"%PDF-" + b"0" * (5 * 1024 * 1024))
    assert resp.status_code == 413


def test_cv_daily_limit(cv_client):
    cv_client.calls["uploads_today"] = 5
    resp = post_cv(cv_client)
    assert resp.status_code == 429


def test_cv_success_saves_grounded_entries(cv_client):
    resp = post_cv(cv_client)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["entries_saved"] == 1
    assert body["model"] == "fake-model"
    assert cv_client.calls["path"].endswith("/cv")
    assert cv_client.calls["row"]["prompt_version"] == "cv-extract-v1"
    assert cv_client.calls["updates"][-1] == {"status": "done"}
    # Teks yang dikirim ke penyimpanan profil sudah lewat grounding.
    assert cv_client.calls["saved"][0]["title"] == "Data Analyst Intern"


def test_cv_llm_failure_is_logged_and_reported(cv_client, monkeypatch):
    llm = FakeLLM([LLMError("x"), LLMError("y")])
    monkeypatch.setattr(cv_api, "get_llm", lambda s: llm)
    resp = post_cv(cv_client)
    assert resp.status_code == 502
    assert cv_client.calls["updates"][-1]["status"] == "failed"
    assert cv_client.calls["saved"] is None
