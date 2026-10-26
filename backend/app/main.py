from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import CurrentUser, get_current_profile, get_current_user, require_admin
from app.config import Settings, get_settings
from app.cv_api import router as cv_router
from app.jobs_api import router as jobs_router
from app.match_api import router as match_router
from app.supabase import ping_database

app = FastAPI(title="Joblytic API", version="0.1.0")
app.include_router(cv_router)
app.include_router(jobs_router)
app.include_router(match_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
async def health(deep: bool = False, settings: Settings = Depends(get_settings)) -> dict:
    """Health check ringan; `?deep=true` juga menyentuh database Supabase."""
    result: dict = {"status": "ok"}
    if deep:
        result["database"] = await ping_database(settings)
    return result


@app.get("/me")
async def me(
    user: CurrentUser = Depends(get_current_user),
    profile: dict = Depends(get_current_profile),
) -> dict:
    return {"user_id": user.id, "email": user.email, "profile": profile}


@app.get("/admin/ping")
async def admin_ping(admin: dict = Depends(require_admin)) -> dict:
    return {"status": "ok", "admin": admin["email"]}
