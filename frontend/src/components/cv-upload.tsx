"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { apiFetch } from "@/lib/api";

type Result = {
  entries_saved: number;
  dropped_entries: number;
  dropped_bullets: number;
};

const MAX_BYTES = 5 * 1024 * 1024;

export function CvUpload({ hasEntries }: { hasEntries: boolean }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setResult(null);

    const form = new FormData(e.currentTarget);
    const file = form.get("file");
    if (!(file instanceof File) || file.size === 0) return setError("Pilih berkas CV dulu.");
    if (file.size > MAX_BYTES) return setError("Ukuran CV maksimal 5 MB.");
    if (
      hasEntries &&
      !window.confirm("Unggah CV baru akan mengganti seluruh isi profil, termasuk perubahan manual. Lanjutkan?")
    ) {
      return;
    }

    form.set("consent", form.get("consent") === "on" ? "true" : "false");
    setPending(true);
    try {
      setResult(await apiFetch<Result>("/cv", { method: "POST", body: form }));
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3 rounded-lg border border-border bg-card p-4">
      <div>
        <h2 className="font-medium">{hasEntries ? "Unggah ulang CV" : "Isi profil dari CV"}</h2>
        <p className="text-sm text-muted">
          PDF atau DOCX berbasis teks, maksimal 5 MB. CV hasil scan belum didukung.
        </p>
      </div>
      <input
        name="file"
        type="file"
        required
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        className="text-sm file:mr-3 file:rounded-md file:border file:border-border file:bg-background file:px-3 file:py-1.5 file:text-sm"
      />
      <label className="flex items-start gap-2 text-sm">
        <input name="consent" type="checkbox" required className="mt-1" />
        <span>
          Saya mengerti bahwa teks CV saya diproses oleh penyedia AI pihak ketiga (Google Gemini)
          untuk mengisi profil. Nama, email, nomor telepon, tautan, dan alamat disensor lebih
          dulu, tetapi jangan unggah data sensitif lain. Di layanan gratis, Google dapat memakai
          masukan untuk memperbaiki produknya.
        </span>
      </label>
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "Memproses CV…" : "Unggah & isi profil"}
        </button>
        {pending && (
          <span className="text-sm text-muted">
            Biasanya beberapa detik; bisa sampai sekitar satu menit bila server sedang bangun.
          </span>
        )}
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
      {result && (
        <p className="text-sm text-accent">
          {result.entries_saved} entri tersimpan. Periksa dan koreksi di bawah.
          {result.dropped_entries + result.dropped_bullets > 0 &&
            ` ${result.dropped_entries} entri dan ${result.dropped_bullets} butir dibuang karena tidak ditemukan di teks CV.`}
        </p>
      )}
    </form>
  );
}
