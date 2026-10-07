"use client";

import { useActionState } from "react";
import type { FormState } from "@/app/applications/actions";
import { STAGES, type Application } from "@/lib/applications";

export const inputClass =
  "w-full rounded-md border border-border bg-card px-3 py-2 text-sm outline-none focus:border-accent";

type Props = {
  action: (prev: FormState, form: FormData) => Promise<FormState>;
  initial?: Application;
  submitLabel: string;
};

// Untuk lamaran baru, tahap awal bisa dipilih; untuk lamaran yang sudah ada,
// tahap diubah lewat kontrol tersendiri supaya riwayatnya tercatat jelas.
export function ApplicationForm({ action, initial, submitLabel }: Props) {
  const [state, formAction, pending] = useActionState(action, {});

  return (
    <form action={formAction} className="grid gap-4 sm:grid-cols-2">
      <label className="flex flex-col gap-1 text-sm">
        Perusahaan *
        <input
          name="company"
          required
          maxLength={200}
          defaultValue={initial?.company}
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Posisi *
        <input
          name="position"
          required
          maxLength={200}
          defaultValue={initial?.position}
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Lokasi
        <input
          name="location"
          maxLength={200}
          defaultValue={initial?.location ?? ""}
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Tautan lowongan
        <input
          name="source_url"
          type="url"
          maxLength={2000}
          placeholder="https://"
          defaultValue={initial?.source_url ?? ""}
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Tanggal melamar
        <input
          name="applied_at"
          type="date"
          defaultValue={initial?.applied_at ?? ""}
          className={inputClass}
        />
        <span className="text-xs text-muted">
          Terisi otomatis saat tahap pertama kali berubah dari Disiapkan.
        </span>
      </label>
      {!initial && (
        <label className="flex flex-col gap-1 text-sm">
          Tahap awal
          <select name="stage" defaultValue="prepared" className={inputClass}>
            {STAGES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="flex flex-col gap-1 text-sm sm:col-span-2">
        Catatan
        <textarea
          name="notes"
          rows={4}
          maxLength={10000}
          defaultValue={initial?.notes ?? ""}
          className={inputClass}
        />
      </label>

      <div className="flex items-center gap-3 sm:col-span-2">
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "Menyimpan…" : submitLabel}
        </button>
        {state.error && <p className="text-sm text-danger">{state.error}</p>}
        {state.ok && !pending && <p className="text-sm text-accent">Tersimpan.</p>}
      </div>
    </form>
  );
}
