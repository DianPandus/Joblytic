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


async def ping_database(settings: Settings) -> bool:
    headers = {"apikey": settings.supabase_publishable_key}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(_rest_url(settings, "rpc/ping"), headers=headers, json={})
        return resp.status_code == 200
    except httpx.HTTPError:
        return False
