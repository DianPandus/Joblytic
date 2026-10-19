"""Pemeriksaan grounding: keluaran LLM harus bisa ditemukan di teks sumbernya."""

import re

WORD_RE = re.compile(r"[a-z0-9+#]+")


def words(text: str) -> list[str]:
    return [w for w in WORD_RE.findall(text.lower()) if len(w) >= 2 or w in {"c", "r"}]


def supported(fragment: str, source_words: set[str], threshold: float = 0.7) -> bool:
    """True bila minimal `threshold` dari kata di `fragment` muncul di teks sumber."""
    fragment_words = words(fragment)
    if not fragment_words:
        return False
    return sum(w in source_words for w in fragment_words) / len(fragment_words) >= threshold


def clean(value: str | None, limit: int) -> str | None:
    value = (value or "").strip()
    return value[:limit] or None
