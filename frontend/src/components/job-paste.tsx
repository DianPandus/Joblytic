"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { inputClass } from "@/components/application-form";
import { apiFetch } from "@/lib/api";

type Result = { id: string; cached: boolean; dropped?: number };

const MIN_CHARS = 80;
const MAX_CHARS = 20000;

export function JobPaste() {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [length, setLength] = useState(0);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const form = new FormData(e.currentTarget);
    const text = String(form.get("text") ?? "").trim();
    if (text.length < MIN_CHARS) {
      return setError("Teks lowongan terlalu pendek. Tempel deskripsi lowongan selengkapnya.");
    }

    setPending(true);
    try {
      const result = await apiFetch<Result>("/jobs/extract", {
        method: "POST",
        body: JSON.stringify({ text, source_url: String(form.get("source_url") ?? "") || null }),
      });
      const params = new URLSearchParams();
      if (result.cached) params.set("cached", "1");
      if (result.dropped) params.set("dropped", String(result.dropped));
      router.push(`/jobs/${result.id}${params.size ? `?${params}` : ""}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
      <div>
        <h2 className="font-medium">Analisis lowongan baru</h2>
        <p className="text-sm text-muted">
          Tempel teks lowongan selengkapnya (posisi, kualifikasi, tanggung jawab). Teks diproses
          oleh Google Gemini; hasilnya bisa kamu koreksi sebelum dipakai.
        </p>
      </div>
      <textarea
        name="text"
        required
        rows={10}
        maxLength={MAX_CHARS}
        onChange={(e) => setLength(e.target.value.length)}
        placeholder="Tempel deskripsi lowongan di sini…"
        className={inputClass}
      />
      <p className="-mt-2 text-right text-xs text-muted">
        {length.toLocaleString("id-ID")} / {MAX_CHARS.toLocaleString("id-ID")}
      </p>
      <label className="flex flex-col gap-1 text-sm">
        Tautan lowongan (opsional)
        <input name="source_url" type="url" maxLength={2000} placeholder="https://…" className={inputClass} />
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "Membaca lowongan…" : "Analisis"}
        </button>
        {pending && (
          <span className="text-sm text-muted">
            Biasanya beberapa detik; bisa sampai sekitar satu menit bila server sedang bangun.
          </span>
        )}
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
    </form>
  );
}
