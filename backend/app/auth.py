"""Verifikasi token Supabase Auth dan pemeriksaan peran di backend."""

from dataclasses import dataclass
from functools import lru_cache

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings, get_settings
from app.supabase import fetch_own_profile

bearer = HTTPBearer(auto_error=False)

ASYMMETRIC_ALGS = ["ES256", "RS256", "EdDSA"]


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str | None
    token: str


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True, lifespan=600)


def _signing_key(token: str, settings: Settings):
    if not settings.supabase_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Server belum dikonfigurasi: SUPABASE_URL kosong"
        )
    try:
        return _jwks_client(settings.jwks_url).get_signing_key_from_jwt(token).key
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Gagal mengambil kunci verifikasi dari Supabase"
        ) from exc


def decode_token(token: str, settings: Settings) -> dict:
    try:
        header = jwt.get_unverified_header(token)
        alg = header.get("alg")
        if alg == "HS256":
            if not settings.supabase_jwt_secret:
                raise jwt.InvalidTokenError("HS256 token but no JWT secret configured")
            key = settings.supabase_jwt_secret
            algorithms = ["HS256"]
        elif alg in ASYMMETRIC_ALGS:
            key = _signing_key(token, settings)
            algorithms = [alg]
        else:
            raise jwt.InvalidTokenError(f"unsupported alg: {alg}")

        return jwt.decode(
            token,
            key,
            algorithms=algorithms,
            audience="authenticated",
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau kedaluwarsa",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Butuh login",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = decode_token(creds.credentials, settings)
    return CurrentUser(id=claims["sub"], email=claims.get("email"), token=creds.credentials)


async def get_current_profile(
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        profile = await fetch_own_profile(user, settings)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Gagal membaca profil dari Supabase (HTTP {exc.response.status_code})",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Tidak bisa menghubungi Supabase"
        ) from exc
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profil akun tidak ditemukan")
    if not profile.get("is_active", True):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Akun dinonaktifkan")
    return profile


async def require_admin(profile: dict = Depends(get_current_profile)) -> dict:
    if profile.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Khusus admin")
    return profile
