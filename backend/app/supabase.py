"""Akses Supabase lewat PostgREST memakai token pengguna, sehingga RLS selalu berlaku."""

from typing import TYPE_CHECKING

import httpx

from app.config import Settings

if TYPE_CHECKING:
    from app.auth import CurrentUser

TIMEOUT = httpx.Timeout(10.0)


def _rest_url(settings: Settings, path: str) -> str:
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}"


async def fetch_own_profile(user: "CurrentUser", settings: Settings) -> dict | None:
    headers = {
        "apikey": settings.supabase_publishable_key,
        "Authorization": f"Bearer {user.token}",
    }
    params = {"id": f"eq.{user.id}", "select": "id,email,full_name,role,is_active,created_at"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(_rest_url(settings, "profiles"), headers=headers, params=params)
        resp.raise_for_status()
        rows = resp.json()
    return rows[0] if rows else None


async def ping_database(settings: Settings) -> str:
    """Mengembalikan "ok" atau alasan singkat kegagalan (tanpa membocorkan kunci)."""
    if not settings.supabase_url or not settings.supabase_publishable_key:
        return "not_configured"
    headers = {"apikey": settings.supabase_publishable_key}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(_rest_url(settings, "rpc/ping"), headers=headers, json={})
    except httpx.HTTPError as exc:
        return f"unreachable ({type(exc).__name__})"
    return "ok" if resp.status_code == 200 else f"http_{resp.status_code}"
