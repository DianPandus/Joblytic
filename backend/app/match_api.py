from dataclasses import asdict
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app import supabase
from app.auth import CurrentUser, get_current_profile, get_current_user
from app.config import Settings, get_settings
from app.matching import DEFAULT_WEIGHTS, Job, MatchResult, ProfileEntry, gaps, match
from app.usage import today_wib

router = APIRouter()

JOB_COLUMNS = (
    "id,required_skills,preferred_skills,education_level,education_fields,min_experience_years"
)
PROFILE_COLUMNS = (
    "id,section,title,organization,start_month,end_month,is_current,description,position,"
    "profile_bullets(id,position,text)"
)


def _evidence_ids(value, entry_ids: set[str], bullet_ids: set[str]) -> None:
    if isinstance(value, dict):
        if "entry_id" in value:
            entry_ids.add(value["entry_id"])
            if value.get("bullet_id"):
                bullet_ids.add(value["bullet_id"])
        for item in value.values():
            _evidence_ids(item, entry_ids, bullet_ids)
    elif isinstance(value, list):
        for item in value:
            _evidence_ids(item, entry_ids, bullet_ids)


def serialize(result: MatchResult, entries: list[ProfileEntry]) -> dict:
    """Hasil sebagai JSON, plus teks entri/butir yang dirujuk bukti supaya bisa ditampilkan."""
    data = asdict(result)
    entry_ids: set[str] = set()
    bullet_ids: set[str] = set()
    _evidence_ids(data["categories"], entry_ids, bullet_ids)
    data["gaps"] = gaps(result)
    data["sources"] = {
        "entries": {
            e.id: {"section": e.section, "title": e.title, "organization": e.organization}
            for e in entries
            if e.id in entry_ids
        },
        "bullets": {b.id: b.text for e in entries for b in e.bullets if b.id in bullet_ids},
    }
    return data


@router.post("/jobs/{job_id}/match")
async def match_job_posting(
    job_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    _profile: dict = Depends(get_current_profile),  # menolak akun nonaktif
    settings: Settings = Depends(get_settings),
) -> dict:
    """Hitung skor kecocokan profil dengan lowongan dan simpan snapshot-nya."""
    try:
        jobs = await supabase.select_rows(
            user, settings, "job_postings", {"select": JOB_COLUMNS, "id": f"eq.{job_id}"}
        )
        if not jobs:  # RLS: lowongan milik pengguna lain juga tidak ditemukan
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Lowongan tidak ditemukan.")
        rows = await supabase.select_rows(
            user, settings, "profile_entries", {"select": PROFILE_COLUMNS, "order": "position"}
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Database tidak bisa dihubungi."
        ) from exc

    entries = [ProfileEntry.from_row(r) for r in rows]
    result = match(Job.from_row(jobs[0]), entries, today_wib(), DEFAULT_WEIGHTS)
    data = serialize(result, entries)

    try:
        await supabase.upsert_row(
            user,
            settings,
            "job_matches",
            {
                "job_posting_id": str(job_id),
                "score": result.score,
                "result": data,
                "weights": DEFAULT_WEIGHTS,
                "scorer_version": result.scorer_version,
            },
            on_conflict="job_posting_id",
        )
    except httpx.HTTPError:
        pass  # skor tetap ditampilkan walau snapshot gagal disimpan
    return {**data, "profile_entries": len(entries)}
