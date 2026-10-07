from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.config import Settings, get_settings
from app.main import app
from tests.helpers import EC_KEY, JWT_SECRET, SUPABASE_URL, profile


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def client(monkeypatch):
    settings = Settings(
        supabase_url=SUPABASE_URL,
        supabase_publishable_key="pk",
        supabase_jwt_secret=JWT_SECRET,
        gemini_api_key="test-key",
    )
    app.dependency_overrides[get_settings] = lambda: settings

    fake_jwks = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=EC_KEY.public_key())
    )
    monkeypatch.setattr(auth, "_jwks_client", lambda url: fake_jwks)

    state = {"profile": profile()}

    async def fake_fetch(user, settings):
        return state["profile"]

    monkeypatch.setattr(auth, "fetch_own_profile", fake_fetch)

    with TestClient(app) as c:
        c.state = state
        yield c
    app.dependency_overrides.clear()
