"use client";

import { useActionState, useState } from "react";
import type { FormState } from "@/app/applications/actions";
import { inputClass } from "@/components/application-form";
import { type ProfileEntry, type Section, sectionInfo } from "@/lib/profile";

type Props = {
  section: Section;
  entry?: ProfileEntry;
  action: (prev: FormState, form: FormData) => Promise<FormState>;
};

const month = (value: string | null | undefined) => value?.slice(0, 7) ?? "";

export function EntryForm({ section, entry, action }: Props) {
  const info = sectionInfo(section);
  const [state, formAction, pending] = useActionState(action, {});
  const [isCurrent, setIsCurrent] = useState(entry?.is_current ?? false);

  return (
    <form action={formAction} className="grid gap-3 sm:grid-cols-2">
      <label className="flex flex-col gap-1 text-sm sm:col-span-2">
        {info.dated ? "Judul (jabatan, gelar, nama proyek, …) *" : `Nama ${info.label.toLowerCase()} *`}
        <input name="title" required maxLength={300} defaultValue={entry?.title} className={inputClass} />
      </label>

      {info.dated && (
        <>
          <label className="flex flex-col gap-1 text-sm">
            {info.orgLabel}
            <input
              name="organization"
              maxLength={300}
              defaultValue={entry?.organization ?? ""}
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Lokasi
            <input
              name="location"
              maxLength={200}
              defaultValue={entry?.location ?? ""}
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Mulai
            <input
              name="start_month"
              type="month"
              defaultValue={month(entry?.start_month)}
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            Selesai
            <input
              name="end_month"
              type="month"
              disabled={isCurrent}
              defaultValue={month(entry?.end_month)}
              className={inputClass}
            />
            <span className="flex items-center gap-2">
              <input
                name="is_current"
                type="checkbox"
                checked={isCurrent}
                onChange={(e) => setIsCurrent(e.target.checked)}
              />
              Masih berlangsung
            </span>
          </label>
        </>
      )}

      <label className="flex flex-col gap-1 text-sm sm:col-span-2">
        {info.dated ? "Keterangan (mis. IPK)" : "Keterangan (mis. tingkat kemahiran)"}
        <input
          name="description"
          maxLength={2000}
          defaultValue={entry?.description ?? ""}
          className={inputClass}
        />
      </label>

      {info.dated && (
        <label className="flex flex-col gap-1 text-sm sm:col-span-2">
          Butir pencapaian/tanggung jawab (satu per baris)
          <textarea
            name="bullets"
            rows={4}
            defaultValue={entry?.profile_bullets.map((b) => b.text).join("\n")}
            className={inputClass}
          />
        </label>
      )}

      <div className="flex items-center gap-3 sm:col-span-2">
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-foreground hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "Menyimpan…" : entry ? "Simpan" : "Tambah"}
        </button>
        {state.error && <p className="text-sm text-danger">{state.error}</p>}
        {state.ok && !pending && <p className="text-sm text-accent">Tersimpan.</p>}
      </div>
    </form>
  );
}
