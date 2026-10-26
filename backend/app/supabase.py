"""Akses Supabase lewat PostgREST memakai token pengguna, sehingga RLS selalu berlaku."""

from typing import TYPE_CHECKING

import httpx

from app.config import Settings

if TYPE_CHECKING:
    from app.auth import CurrentUser

TIMEOUT = httpx.Timeout(10.0)


def _rest_url(settings: Settings, path: str) -> str:
    return f"{settings.supabase_url.rstrip('/')}/rest/v1/{path}"


def _user_headers(user: "CurrentUser", settings: Settings) -> dict[str, str]:
    return {
        "apikey": settings.supabase_publishable_key,
        "Authorization": f"Bearer {user.token}",
    }


async def fetch_own_profile(user: "CurrentUser", settings: Settings) -> dict | None:
    headers = _user_headers(user, settings)
    params = {"id": f"eq.{user.id}", "select": "id,email,full_name,role,is_active,created_at"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(_rest_url(settings, "profiles"), headers=headers, params=params)
        resp.raise_for_status()
        rows = resp.json()
    return rows[0] if rows else None


async def count_cv_uploads_since(user: "CurrentUser", settings: Settings, since: str) -> int:
    params = {"select": "id", "created_at": f"gte.{since}"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            _rest_url(settings, "cv_uploads"), headers=_user_headers(user, settings), params=params
        )
        resp.raise_for_status()
    return len(resp.json())


async def upload_cv_file(
    user: "CurrentUser", settings: Settings, path: str, data: bytes, mime: str
) -> None:
    url = f"{settings.supabase_url.rstrip('/')}/storage/v1/object/cvs/{path}"
    headers = {**_user_headers(user, settings), "Content-Type": mime, "x-upsert": "true"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(url, headers=headers, content=data)
        resp.raise_for_status()


async def insert_cv_upload(user: "CurrentUser", settings: Settings, row: dict) -> str:
    headers = {**_user_headers(user, settings), "Prefer": "return=representation"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            _rest_url(settings, "cv_uploads"), headers=headers, params={"select": "id"}, json=row
        )
        resp.raise_for_status()
    return resp.json()[0]["id"]


async def update_cv_upload(
    user: "CurrentUser", settings: Settings, upload_id: str, fields: dict
) -> None:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.patch(
            _rest_url(settings, "cv_uploads"),
            headers=_user_headers(user, settings),
            params={"id": f"eq.{upload_id}"},
            json=fields,
        )
        resp.raise_for_status()


async def replace_profile_from_cv(
    user: "CurrentUser", settings: Settings, entries: list[dict]
) -> int:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            _rest_url(settings, "rpc/replace_profile_from_cv"),
            headers=_user_headers(user, settings),
            json={"entries": entries},
        )
        resp.raise_for_status()
    return resp.json()


async def select_rows(
    user: "CurrentUser", settings: Settings, table: str, params: dict[str, str]
) -> list[dict]:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            _rest_url(settings, table), headers=_user_headers(user, settings), params=params
        )
        resp.raise_for_status()
    return resp.json()


async def insert_row(
    user: "CurrentUser", settings: Settings, table: str, row: dict, returning: str | None = None
) -> dict | None:
    """Insert satu baris; bila `returning` diisi, kembalikan kolom tersebut dari baris baru."""
    headers = _user_headers(user, settings)
    params = {}
    if returning:
        headers["Prefer"] = "return=representation"
        params["select"] = returning
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            _rest_url(settings, table), headers=headers, params=params, json=row
        )
        resp.raise_for_status()
    return resp.json()[0] if returning else None


async def upsert_row(
    user: "CurrentUser", settings: Settings, table: str, row: dict, on_conflict: str
) -> None:
    """Insert, atau timpa baris yang bentrok di kolom unik `on_conflict`."""
    headers = {**_user_headers(user, settings), "Prefer": "resolution=merge-duplicates"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            _rest_url(settings, table),
            headers=headers,
            params={"on_conflict": on_conflict},
            json=row,
        )
        resp.raise_for_status()


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
