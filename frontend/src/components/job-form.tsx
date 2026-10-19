"use client";

import { useActionState } from "react";
import type { FormState } from "@/app/applications/actions";
import { inputClass } from "@/components/application-form";
import { EDUCATION_LEVELS, type JobPosting } from "@/lib/jobs";

type Props = {
  job: JobPosting;
  action: (prev: FormState, form: FormData) => Promise<FormState>;
};

function ListField({ name, label, hint, values, rows = 4 }: {
  name: string;
  label: string;
  hint: string;
  values: string[];
  rows?: number;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm sm:col-span-2">
      <span>
        {label} <span className="text-xs text-muted">({hint})</span>
      </span>
      <textarea name={name} rows={rows} defaultValue={values.join("\n")} className={inputClass} />
    </label>
  );
}

export function JobForm({ job, action }: Props) {
  const [state, formAction, pending] = useActionState(action, {});

  return (
    <form action={formAction} className="grid gap-4 sm:grid-cols-2">
      <label className="flex flex-col gap-1 text-sm">
        Posisi
        <input name="position" maxLength={200} defaultValue={job.position ?? ""} className={inputClass} />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Perusahaan
        <input name="company" maxLength={200} defaultValue={job.company ?? ""} className={inputClass} />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Lokasi
        <input name="location" maxLength={200} defaultValue={job.location ?? ""} className={inputClass} />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Tautan lowongan
        <input
          name="source_url"
          type="url"
          maxLength={2000}
          defaultValue={job.source_url ?? ""}
          className={inputClass}
        />
      </label>

      <ListField
        name="required_skills"
        label="Skill wajib"
        hint="satu per baris"
        values={job.required_skills}
        rows={6}
      />
      <ListField
        name="preferred_skills"
        label="Skill nilai tambah"
        hint="satu per baris"
        values={job.preferred_skills}
      />

      <label className="flex flex-col gap-1 text-sm">
        Pendidikan minimal
        <select name="education_level" defaultValue={job.education_level ?? ""} className={inputClass}>
          <option value="">Tidak disebut</option>
          {EDUCATION_LEVELS.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span>
          Pengalaman minimal (tahun){" "}
          <span className="text-xs text-muted">(0 = fresh graduate, kosong = tidak disebut)</span>
        </span>
        <input
          name="min_experience_years"
          inputMode="decimal"
          maxLength={5}
          defaultValue={job.min_experience_years ?? ""}
          className={inputClass}
        />
      </label>
      <ListField
        name="education_fields"
        label="Jurusan"
        hint="satu per baris, kosongkan bila semua jurusan"
        values={job.education_fields}
        rows={3}
      />
      <ListField
        name="responsibilities"
        label="Tanggung jawab utama"
        hint="satu per baris"
        values={job.responsibilities}
        rows={6}
      />

      <div className="flex items-center gap-3 sm:col-span-2">
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:opacity-90 disabled:opacity-50"
        >
          {pending ? "Menyimpan…" : "Simpan koreksi"}
        </button>
        {state.error && <p className="text-sm text-danger">{state.error}</p>}
        {state.ok && !pending && <p className="text-sm text-accent">Tersimpan.</p>}
      </div>
    </form>
  );
}
