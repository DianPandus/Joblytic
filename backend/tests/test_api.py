import time

import httpx
import jwt
import pytest

from app import auth
from app.config import Settings, get_settings
from app.main import app
from tests.helpers import SUPABASE_URL, USER_ID, bearer, make_token, profile


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


def test_supabase_error_on_profile_is_clear_503(client, monkeypatch):
    async def failing_fetch(user, settings):
        request = httpx.Request("GET", f"{SUPABASE_URL}/rest/v1/profiles")
        response = httpx.Response(401, request=request)
        raise httpx.HTTPStatusError("unauthorized", request=request, response=response)

    monkeypatch.setattr(auth, "fetch_own_profile", failing_fetch)
    resp = client.get("/me", headers=bearer(make_token()))
    assert resp.status_code == 503
    assert "HTTP 401" in resp.json()["detail"]


def test_deep_health_reports_missing_config(client):
    app.dependency_overrides[get_settings] = lambda: Settings(supabase_url="")
    assert client.get("/health?deep=true").json()["database"] == "not_configured"


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
