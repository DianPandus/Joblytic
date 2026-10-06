import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app import auth
from app.config import Settings, get_settings
from app.main import app

SUPABASE_URL = "https://example.supabase.co"
JWT_SECRET = "test-secret-at-least-32-characters-long!!"
USER_ID = "11111111-1111-1111-1111-111111111111"

EC_KEY = ec.generate_private_key(ec.SECP256R1())


def make_token(*, alg="HS256", sub=USER_ID, exp_offset=3600, aud="authenticated", iss=None):
    claims = {
        "sub": sub,
        "email": "dian@example.com",
        "aud": aud,
        "iss": iss or f"{SUPABASE_URL}/auth/v1",
        "exp": int(time.time()) + exp_offset,
        "role": "authenticated",
    }
    key = JWT_SECRET if alg == "HS256" else EC_KEY
    return jwt.encode(claims, key, algorithm=alg, headers={"kid": "test"})


def profile(role="user", is_active=True):
    return {
        "id": USER_ID,
        "email": "dian@example.com",
        "full_name": "Dian",
        "role": role,
        "is_active": is_active,
    }


@pytest.fixture
def client(monkeypatch):
    settings = Settings(
        supabase_url=SUPABASE_URL,
        supabase_publishable_key="pk",
        supabase_jwt_secret=JWT_SECRET,
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


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_me_requires_token(client):
    assert client.get("/me").status_code == 401


@pytest.mark.parametrize("alg", ["HS256", "ES256"])
def test_me_with_valid_token(client, alg):
    resp = client.get("/me", headers=bearer(make_token(alg=alg)))
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == USER_ID
    assert body["profile"]["role"] == "user"


@pytest.mark.parametrize(
    "token",
    [
        make_token(exp_offset=-10),
        make_token(aud="anon"),
        make_token(iss="https://evil.example.com/auth/v1"),
        "not-a-jwt",
    ],
    ids=["expired", "wrong-aud", "wrong-iss", "garbage"],
)
def test_me_rejects_bad_tokens(client, token):
    assert client.get("/me", headers=bearer(token)).status_code == 401


def test_hs256_wrong_secret_rejected(client):
    forged = jwt.encode(
        {
            "sub": USER_ID,
            "aud": "authenticated",
            "iss": f"{SUPABASE_URL}/auth/v1",
            "exp": int(time.time()) + 60,
        },
        "another-secret-that-is-also-32-chars-long",
        algorithm="HS256",
    )
    assert client.get("/me", headers=bearer(forged)).status_code == 401


def test_missing_supabase_url_is_clear_error(client):
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_url="")
    resp = client.get("/me", headers=bearer(make_token(alg="ES256")))
    assert resp.status_code == 503
    assert "SUPABASE_URL" in resp.json()["detail"]


def test_inactive_account_forbidden(client):
    client.state["profile"] = profile(is_active=False)
    assert client.get("/me", headers=bearer(make_token())).status_code == 403


def test_admin_route_forbidden_for_user(client):
    assert client.get("/admin/ping", headers=bearer(make_token())).status_code == 403


def test_admin_route_allowed_for_admin(client):
    client.state["profile"] = profile(role="admin")
    resp = client.get("/admin/ping", headers=bearer(make_token()))
    assert resp.status_code == 200
    assert resp.json()["admin"] == "dian@example.com"
