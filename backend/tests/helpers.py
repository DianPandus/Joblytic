"""Helper bersama untuk test (modul biasa, supaya hanya di-import sekali)."""

import time

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

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


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


class FakeLLM:
    model = "fake-model"

    def __init__(self, responses):
        self.responses = list(responses)
        self.systems = []

    async def generate_json(self, system, prompt, schema):
        self.systems.append(system)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
