"""Adapter penyedia LLM. Kode lain hanya memakai `LLMClient`, supaya penyedia mudah diganti."""

import json
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings

T = TypeVar("T", bound=BaseModel)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = httpx.Timeout(60.0)


class LLMError(Exception):
    """Kegagalan memanggil LLM (jaringan, kuota, atau keluaran tidak valid)."""


class LLMQuotaError(LLMError):
    pass


class LLMClient(Protocol):
    model: str

    async def generate_json(self, system: str, prompt: str, schema: type[T]) -> T: ...


class GeminiClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    async def generate_json(self, system: str, prompt: str, schema: type[T]) -> T:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
                "responseJsonSchema": schema.model_json_schema(),
            },
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    GEMINI_URL.format(model=self.model),
                    headers={"x-goog-api-key": self.api_key},
                    json=body,
                )
        except httpx.HTTPError as exc:
            raise LLMError(f"Gagal menghubungi Gemini: {type(exc).__name__}") from exc

        if resp.status_code == 429:
            raise LLMQuotaError("Kuota Gemini habis")
        if resp.status_code != 200:
            raise LLMError(f"Gemini membalas HTTP {resp.status_code}")

        try:
            parts = resp.json()["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            return schema.model_validate(json.loads(text))
        except (KeyError, IndexError, json.JSONDecodeError, ValidationError) as exc:
            raise LLMError("Keluaran Gemini tidak sesuai skema") from exc


def get_llm(settings: Settings) -> LLMClient:
    if not settings.gemini_api_key:
        raise LLMError("GEMINI_API_KEY belum diisi")
    return GeminiClient(settings.gemini_api_key, settings.gemini_model)
