from datetime import UTC, datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app import supabase
from app.auth import CurrentUser, get_current_profile, get_current_user
from app.config import Settings, get_settings
from app.cv import (
    MAX_FILE_BYTES,
    PROMPT_VERSION,
    CVError,
    detect_type,
    extract_profile,
    extract_text,
    redact,
)
from app.llm import LLMError, LLMQuotaError, get_llm

router = APIRouter()

WIB = timezone(timedelta(hours=7))


def _start_of_today_wib() -> str:
    now = datetime.now(WIB)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


@router.post("/cv")
async def upload_cv(
    file: UploadFile = File(...),
    consent: bool = Form(False),
    user: CurrentUser = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Unggah CV, ekstrak ke profil terstruktur, dan ganti entri profil yang lama."""
    if not consent:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Setujui pemberitahuan pemrosesan CV oleh penyedia AI pihak ketiga terlebih dulu.",
        )

    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Ukuran CV maksimal 5 MB.")

    try:
        mime = detect_type(data)
        text = extract_text(data, mime)
        llm = get_llm(settings)
    except CVError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Layanan AI belum dikonfigurasi di server."
        ) from exc

    try:
        used = await supabase.count_cv_uploads_since(user, settings, _start_of_today_wib())
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Database tidak bisa dihubungi."
        ) from exc
    if used >= settings.cv_uploads_per_day:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Batas unggah CV hari ini ({settings.cv_uploads_per_day}x) sudah tercapai. "
            "Coba lagi besok.",
        )

    # Satu berkas CV per pengguna; unggahan baru menimpa yang lama.
    storage_path = f"{user.id}/cv"
    try:
        await supabase.upload_cv_file(user, settings, storage_path, data, mime)
        upload_id = await supabase.insert_cv_upload(
            user,
            settings,
            {
                "storage_path": storage_path,
                "file_name": (file.filename or "cv")[:255],
                "mime_type": mime,
                "size_bytes": len(data),
                "consent_at": datetime.now(UTC).isoformat(),
                "llm_model": llm.model,
                "prompt_version": PROMPT_VERSION,
            },
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Gagal menyimpan berkas CV. Coba lagi."
        ) from exc

    try:
        result = await extract_profile(llm, redact(text, profile.get("full_name")))
        if not result.entries:
            raise CVError("Tidak ada isi CV yang bisa dikenali. Periksa kembali berkasnya.")
        saved = await supabase.replace_profile_from_cv(user, settings, result.entries)
    except (CVError, LLMError, httpx.HTTPError) as exc:
        await _mark_failed(user, settings, upload_id, exc)
        if isinstance(exc, CVError):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        if isinstance(exc, LLMQuotaError):
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Kuota layanan AI sedang habis. Coba lagi beberapa saat lagi.",
            ) from exc
        if isinstance(exc, LLMError):
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY, "Gagal memproses CV dengan AI. Coba lagi."
            ) from exc
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Gagal menyimpan profil. Coba lagi."
        ) from exc

    await supabase.update_cv_upload(user, settings, upload_id, {"status": "done"})
    return {
        "entries_saved": saved,
        "dropped_entries": result.dropped_entries,
        "dropped_bullets": result.dropped_bullets,
        "model": llm.model,
        "prompt_version": PROMPT_VERSION,
    }


async def _mark_failed(user: CurrentUser, settings: Settings, upload_id: str, exc: Exception):
    try:
        await supabase.update_cv_upload(
            user, settings, upload_id, {"status": "failed", "error": str(exc)[:500]}
        )
    except httpx.HTTPError:
        pass  # log kegagalan bukan alasan untuk menyembunyikan error aslinya
