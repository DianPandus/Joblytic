"use client";

import { useActionState } from "react";
import type { FormState } from "@/app/applications/actions";
import { inputClass } from "@/components/application-form";
import { EVENT_KINDS } from "@/lib/applications";

export function EventForm({
  action,
}: {
  action: (prev: FormState, form: FormData) => Promise<FormState>;
}) {
  const [state, formAction, pending] = useActionState(action, {});

  return (
    <form action={formAction} className="grid gap-3 sm:grid-cols-3">
      <label className="flex flex-col gap-1 text-sm">
        Jenis
        <select name="kind" defaultValue="interview" className={inputClass}>
          {EVENT_KINDS.map((k) => (
            <option key={k.value} value={k.value}>
              {k.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Judul *
        <input
          name="title"
          required
          maxLength={200}
          placeholder="mis. Wawancara HR"
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Waktu (WIB) *
        <input name="scheduled_at" type="datetime-local" required className={inputClass} />
      </label>
      <label className="flex flex-col gap-1 text-sm sm:col-span-3">
        Catatan
        <input name="notes" maxLength={2000} className={inputClass} />
      </label>
      <div className="flex items-center gap-3 sm:col-span-3">
        <button
          type="submit"
          disabled={pending}
          className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-card disabled:opacity-50"
        >
          {pending ? "Menyimpan…" : "Tambah jadwal"}
        </button>
        {state.error && <p className="text-sm text-danger">{state.error}</p>}
      </div>
    </form>
  );
}
