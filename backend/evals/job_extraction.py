"""Evaluasi akurasi ekstraksi lowongan terhadap label manual (PRD bagian 10, target >= 90%).

Set data ada di `evals/jobs/`:
    postings/<nama>.txt   teks lowongan apa adanya
    labels/<nama>.json    jawaban benar, ditulis/dikoreksi manual

Perintah (dijalankan dari folder backend, memakai GEMINI_API_KEY di .env):
    python -m evals.job_extraction draft
        Buat draf label dari keluaran model untuk posting yang belum berlabel. Draf WAJIB
        dikoreksi terhadap teks lowongannya, lalu ubah "verified" menjadi true.
    python -m evals.job_extraction run
        Jalankan pipeline pada semua label terverifikasi, cetak skor per field, dan simpan
        hasilnya di evals/jobs/results/.
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from app.config import get_settings
from app.jobs import PROMPT_VERSION, JobError, extract_job, validate_text
from app.llm import LLMError, get_llm

ROOT = Path(__file__).parent / "jobs"
POSTINGS, LABELS, RESULTS = ROOT / "postings", ROOT / "labels", ROOT / "results"

SCALAR_FIELDS = ["position", "company", "location", "education_level", "min_experience_years"]
LIST_FIELDS = ["required_skills", "preferred_skills", "education_fields", "responsibilities"]
FUZZY_FIELDS = {"required_skills", "preferred_skills", "responsibilities"}
FIELDS = SCALAR_FIELDS + LIST_FIELDS
TARGET = 0.9

# Kata pengantar yang tidak mengubah skill-nya ("Strong analytical skills" = "analytical").
# Sengaja tanpa "basic" dan "solid" (Visual Basic, SOLID).
SKILL_FILLER = {
    "good", "strong", "excellent", "fluent", "proficiency", "proficient",
    "skill", "skills", "kemampuan", "keterampilan", "mahir",
}  # fmt: skip


# --- Pencocokan ----------------------------------------------------------------


def norm(value) -> str:
    """Bandingkan tanpa peduli huruf besar, spasi, dan tanda baca (kecuali + dan #)."""
    text = re.sub(r"[^\w+#]+", " ", str(value).casefold())
    return " ".join(text.split())


def scalar_match(predicted, expected) -> bool:
    if predicted is None or expected is None:
        return predicted is None and expected is None
    if isinstance(expected, int | float):
        return isinstance(predicted, int | float) and float(predicted) == float(expected)
    return norm(predicted) == norm(expected)


def _strip_filler(text: str) -> str:
    kept = [w for w in text.split() if w not in SKILL_FILLER]
    return " ".join(kept) or text


def _is_acronym(short: str, long: str) -> bool:
    """True bila `short` adalah singkatan `long`, mis. "uat" dan "user acceptance testing"."""
    words = long.split()
    return " " not in short and len(words) >= 2 and short == "".join(w[0] for w in words)


def _same_item(a: str, b: str, fuzzy: bool) -> bool:
    a, b = norm(a), norm(b)
    if a == b:
        return True
    if not fuzzy:
        return False
    a, b = _strip_filler(a), _strip_filler(b)
    if _is_acronym(a, b) or _is_acronym(b, a):
        return True
    return a == b or SequenceMatcher(None, a, b).ratio() >= 0.85


def list_counts(predicted: list[str], expected: list[str], fuzzy: bool) -> tuple[int, int, int]:
    """(benar, jumlah prediksi, jumlah label); tiap label hanya boleh dipasangkan sekali."""
    remaining = list(expected)
    hits = 0
    for item in predicted:
        for i, candidate in enumerate(remaining):
            if _same_item(item, candidate, fuzzy):
                hits += 1
                del remaining[i]
                break
    return hits, len(predicted), len(expected)


def f1(hits: int, n_pred: int, n_label: int) -> float:
    # Dua-duanya kosong berarti model benar mengosongkan field.
    if n_pred == 0 and n_label == 0:
        return 1.0
    return 2 * hits / (n_pred + n_label)


def score(cases: list[tuple[str, dict, dict]]) -> dict:
    """Skor per field: akurasi untuk field tunggal, F1 mikro untuk field daftar."""
    report: dict[str, dict] = {}
    for field in SCALAR_FIELDS:
        wrong = [name for name, pred, label in cases if not scalar_match(pred[field], label[field])]
        report[field] = {
            "metric": "accuracy",
            "score": 1 - len(wrong) / len(cases),
            "errors": wrong,
        }
    for field in LIST_FIELDS:
        totals = [0, 0, 0]
        wrong = []
        for name, pred, label in cases:
            counts = list_counts(pred[field], label[field], fuzzy=field in FUZZY_FIELDS)
            totals = [t + c for t, c in zip(totals, counts, strict=True)]
            if counts[0] != counts[1] or counts[0] != counts[2]:
                wrong.append(name)
        hits, n_pred, n_label = totals
        report[field] = {
            "metric": "f1",
            "score": f1(hits, n_pred, n_label),
            "precision": hits / n_pred if n_pred else 1.0,
            "recall": hits / n_label if n_label else 1.0,
            "errors": wrong,
        }
    return report


# --- Perintah --------------------------------------------------------------------


def _postings() -> list[Path]:
    return sorted(POSTINGS.glob("*.txt"))


def _label_path(posting: Path) -> Path:
    return LABELS / f"{posting.stem}.json"


async def _extract(llm, posting: Path) -> dict:
    text = validate_text(posting.read_text(encoding="utf-8"))
    return (await extract_job(llm, text)).fields


async def _extract_with_retry(llm, posting: Path, delay: float) -> dict:
    """Gemini gratis kadang sibuk atau kena batas per menit; coba sekali lagi setelah jeda."""
    try:
        return await _extract(llm, posting)
    except LLMError as exc:
        print(f"  {posting.name}: {exc}, dicoba ulang")
        await asyncio.sleep(delay * 3)
        return await _extract(llm, posting)


async def draft(delay: float) -> None:
    llm = get_llm(get_settings())
    LABELS.mkdir(parents=True, exist_ok=True)
    todo = [p for p in _postings() if not _label_path(p).exists()]
    print(f"{len(todo)} posting belum berlabel.")
    for i, posting in enumerate(todo):
        if i:
            await asyncio.sleep(delay)
        try:
            fields = await _extract(llm, posting)
        except (LLMError, JobError) as exc:
            print(f"  {posting.name}: GAGAL ({exc})")
            continue
        label = {"verified": False, **fields}
        _label_path(posting).write_text(
            json.dumps(label, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"  {posting.name}: draf ditulis")
    print('Koreksi setiap draf terhadap teks lowongannya, lalu ubah "verified" menjadi true.')


async def run(delay: float) -> None:
    settings = get_settings()
    llm = get_llm(settings)
    labelled = []
    for posting in _postings():
        path = _label_path(posting)
        if path.exists():
            label = json.loads(path.read_text(encoding="utf-8"))
            if label.get("verified"):
                labelled.append((posting, label))
    if not labelled:
        sys.exit("Belum ada label terverifikasi di evals/jobs/labels/.")

    cases, failures = [], {}
    for i, (posting, label) in enumerate(labelled):
        if i:
            await asyncio.sleep(delay)
        try:
            cases.append((posting.stem, await _extract_with_retry(llm, posting, delay), label))
            print(f"  {posting.name}: ok")
        except (LLMError, JobError) as exc:
            failures[posting.stem] = str(exc)
            print(f"  {posting.name}: GAGAL ({exc})")
    if not cases:
        sys.exit("Semua ekstraksi gagal.")

    report = score(cases)
    print(f"\nModel {llm.model}, prompt {PROMPT_VERSION}, {len(cases)} lowongan")
    if failures:
        print(f"Gagal diekstrak (tidak dihitung): {', '.join(failures)}")
    print(f"{'field':<22}{'metrik':<10}{'skor':>7}  status")
    for field, r in report.items():
        status = "lulus" if r["score"] >= TARGET else f"di bawah target ({', '.join(r['errors'])})"
        print(f"{field:<22}{r['metric']:<10}{r['score']:>7.1%}  {status}")

    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out = RESULTS / f"{stamp}_{llm.model}_{PROMPT_VERSION}.json"
    out.write_text(
        json.dumps(
            {
                "model": llm.model,
                "prompt_version": PROMPT_VERSION,
                "n": len(cases),
                "failures": failures,
                "fields": report,
                "predictions": {name: pred for name, pred, _ in cases},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"\nHasil disimpan di {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["draft", "run"])
    parser.add_argument(
        "--delay", type=float, default=5.0, help="jeda antarpanggilan (detik), batas RPM gratis"
    )
    args = parser.parse_args()
    asyncio.run(draft(args.delay) if args.command == "draft" else run(args.delay))


if __name__ == "__main__":
    main()
