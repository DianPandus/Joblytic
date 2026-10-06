from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str = ""
    # Kunci publik (publishable/anon). Dipakai bersama token pengguna supaya
    # RLS di database tetap berlaku untuk setiap query dari backend.
    supabase_publishable_key: str = ""
    # Hanya untuk proyek lama yang masih memakai JWT secret HS256.
    # Proyek baru memakai signing key asimetris yang diverifikasi lewat JWKS.
    supabase_jwt_secret: str = ""
    # Daftar origin frontend dipisah koma, mis. "http://localhost:3000,https://joblytic.vercel.app"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"


@lru_cache
def get_settings() -> Settings:
    return Settings()
