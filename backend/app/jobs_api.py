import time
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app import supabase
from app.auth import CurrentUser, get_current_profile, get_current_user
from app.config import Settings, get_settings
from app.jobs import PROMPT_VERSION, JobError, extract_job, text_hash, validate_text
from app.llm import LLMClient, LLMError, LLMQuotaError, get_llm
from app.usage import start_of_today_wib

router = APIRouter()


class ExtractRequest(BaseModel):
    # Batas mentah longgar; batas sebenarnya dicek setelah spasi dirapikan.
    text: str = Field(max_length=40_000)
    source_url: str | None = Field(default=None, max_length=2000)


def _http_url(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise JobError("Tautan harus berupa URL http:// atau https://.")
    return value


def _db_unavailable() -> HTTPException:
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database tidak bisa dihubungi.")


@router.post("/jobs/extract")
async def extract_job_posting(
    body: ExtractRequest,
    user: CurrentUser = Depends(get_current_user),
    _profile: dict = Depends(get_current_profile),  # menolak akun nonaktif
    settings: Settings = Depends(get_settings),
) -> dict:
    """Ekstrak persyaratan dari teks lowongan dan simpan sebagai lowongan baru."""
    try:
        text = validate_text(body.text)
        source_url = _http_url(body.source_url)
    except JobError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    # Cache: lowongan yang sama tidak diekstrak ulang dan tidak memakai kuota.
    digest = text_hash(text)
    try:
        existing = await supabase.select_rows(
            user, settings, "job_postings", {"select": "id", "text_hash": f"eq.{digest}"}
        )
    except httpx.HTTPError as exc:
        raise _db_unavailable() from exc
    if existing:
        return {"id": existing[0]["id"], "cached": True}

    try:
        llm = get_llm(settings)
    except LLMError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Layanan AI belum dikonfigurasi di server."
        ) from exc

    try:
        used = await supabase.select_rows(
            user,
            settings,
            "llm_usage",
            {
                "select": "id",
                "kind": "eq.job_extract",
                "created_at": f"gte.{start_of_today_wib()}",
            },
        )
    except httpx.HTTPError as exc:
        raise _db_unavailable() from exc
    if len(used) >= settings.job_extractions_per_day:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Batas analisis lowongan hari ini ({settings.job_extractions_per_day}x) sudah "
            "tercapai. Coba lagi besok.",
        )

    started = time.monotonic()
    try:
        result = await extract_job(llm, text)
    except LLMError as exc:
        await _log_usage(user, settings, llm, started, exc)
        if isinstance(exc, LLMQuotaError):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Kuota layanan AI sedang habis. Coba lagi beberapa saat lagi.",
            ) from exc
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, "Gagal membaca lowongan dengan AI. Coba lagi."
        ) from exc
    await _log_usage(user, settings, llm, started, None)

    row = {
        "source_text": text,
        "text_hash": digest,
        "source_url": source_url,
        **result.fields,
        "extracted": result.fields,
        "llm_model": llm.model,
        "prompt_version": PROMPT_VERSION,
    }
    try:
        created = await supabase.insert_row(user, settings, "job_postings", row, returning="id")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:  # tempelan yang sama dikirim dua kali bersamaan
            rows = await supabase.select_rows(
                user, settings, "job_postings", {"select": "id", "text_hash": f"eq.{digest}"}
            )
            if rows:
                return {"id": rows[0]["id"], "cached": True}
        raise _db_unavailable() from exc
    except httpx.HTTPError as exc:
        raise _db_unavailable() from exc

    return {
        "id": created["id"],
        "cached": False,
        "dropped": result.dropped,
        "model": llm.model,
        "prompt_version": PROMPT_VERSION,
    }


async def _log_usage(
    user: CurrentUser,
    settings: Settings,
    llm: LLMClient,
    started: float,
    error: Exception | None,
) -> None:
    try:
        await supabase.insert_row(
            user,
            settings,
            "llm_usage",
            {
                "kind": "job_extract",
                "status": "failed" if error else "ok",
                "llm_model": llm.model,
                "prompt_version": PROMPT_VERSION,
                "latency_ms": round((time.monotonic() - started) * 1000),
                "error": str(error)[:500] if error else None,
            },
        )
    except httpx.HTTPError:
        pass  # log yang gagal ditulis bukan alasan untuk menggagalkan permintaan
