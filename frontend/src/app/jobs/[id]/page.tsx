import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { createApplicationFromJob, deleteJobPosting, updateJobPosting } from "@/app/jobs/actions";
import { AppHeader } from "@/components/app-header";
import { JobForm } from "@/components/job-form";
import { formatDateTime, stageLabel } from "@/lib/applications";
import { type JobPosting, educationLabel, formatYears } from "@/lib/jobs";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Detail lowongan · Joblytic" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function JobDetailPage(props: PageProps<"/jobs/[id]">) {
  const { id } = await props.params;
  if (!UUID.test(id)) notFound();
  const searchParams = await props.searchParams;
  const cached = searchParams.cached === "1";
  const dropped = Number(searchParams.dropped ?? 0) || 0;

  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  if (!claimsData?.claims) redirect(`/login?next=/jobs/${id}`);

  // RLS: lowongan milik pengguna lain tidak akan ditemukan, jadi tampil 404.
  const [{ data }, { data: apps }] = await Promise.all([
    supabase.from("job_postings").select("*").eq("id", id).maybeSingle(),
    supabase.from("applications").select("id, stage").eq("job_posting_id", id).limit(1),
  ]);
  if (!data) notFound();
  const job = data as JobPosting;
  const application = apps?.[0] as { id: string; stage: string } | undefined;

  const education = [educationLabel(job.education_level), job.education_fields.join(", ")]
    .filter(Boolean)
    .join(" · ");

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-10">
      <AppHeader active="/jobs" />

      <section>
        <Link href="/jobs" className="text-sm text-muted hover:text-foreground">
          ← Lowongan
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{job.position ?? "Posisi tanpa nama"}</h1>
        <p className="text-muted">
          {[job.company, job.location].filter(Boolean).join(" · ") || "Perusahaan tidak disebut"}
        </p>
        {job.source_url && (
          <a
            href={job.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-block break-all text-sm text-accent underline"
          >
            Buka tautan lowongan
          </a>
        )}
        {cached && (
          <p className="mt-3 rounded-md border border-border p-3 text-sm text-muted">
            Lowongan ini sudah pernah kamu analisis, jadi hasil sebelumnya yang ditampilkan.
          </p>
        )}
        {dropped > 0 && (
          <p className="mt-3 rounded-md border border-border p-3 text-sm text-muted">
            {dropped} isian dari AI dibuang karena tidak ditemukan di teks lowongan. Periksa
            apakah ada yang terlewat.
          </p>
        )}
      </section>

      <section className="grid gap-4 rounded-lg border border-border bg-card p-4 text-sm sm:grid-cols-2">
        <Skills title="Skill wajib" items={job.required_skills} />
        <Skills title="Skill nilai tambah" items={job.preferred_skills} />
        <div>
          <h2 className="font-medium text-muted">Pendidikan</h2>
          <p className="mt-1">{education || "Tidak disebut"}</p>
        </div>
        <div>
          <h2 className="font-medium text-muted">Pengalaman</h2>
          <p className="mt-1">{formatYears(job.min_experience_years) ?? "Tidak disebut"}</p>
        </div>
        <div className="sm:col-span-2">
          <h2 className="font-medium text-muted">Tanggung jawab utama</h2>
          {job.responsibilities.length === 0 ? (
            <p className="mt-1">Tidak disebut</p>
          ) : (
            <ul className="mt-1 list-disc space-y-0.5 pl-5">
              {job.responsibilities.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="flex flex-wrap items-center gap-3">
        {application ? (
          <Link
            href={`/applications/${application.id}`}
            className="rounded-md border border-accent px-4 py-2 text-sm text-accent hover:bg-card"
          >
            Lihat di tracker ({stageLabel(application.stage)})
          </Link>
        ) : (
          <form action={createApplicationFromJob.bind(null, job.id)}>
            <button className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:opacity-90">
              Simpan sebagai lamaran
            </button>
          </form>
        )}
        <span className="text-sm text-muted">Skor kecocokan dengan profil menyusul di Fase 3.</span>
      </section>

      <details className="rounded-lg border border-border p-4" open={!job.corrected_at}>
        <summary className="cursor-pointer text-sm font-medium">Koreksi hasil ekstraksi</summary>
        <p className="mt-2 text-sm text-muted">
          Periksa terhadap teks lowongan di bawah. Hasil yang sudah dikoreksi inilah yang dipakai
          untuk pencocokan.
        </p>
        <div className="mt-4">
          <JobForm job={job} action={updateJobPosting.bind(null, job.id)} />
        </div>
        <p className="mt-3 text-xs text-muted">
          Diekstrak {formatDateTime(job.created_at)}
          {job.llm_model ? ` · ${job.llm_model}` : ""}
          {job.prompt_version ? ` · ${job.prompt_version}` : ""}
          {job.corrected_at ? ` · dikoreksi ${formatDateTime(job.corrected_at)}` : ""}
        </p>
      </details>

      <details className="rounded-lg border border-border p-4">
        <summary className="cursor-pointer text-sm font-medium">Teks lowongan asli</summary>
        <pre className="mt-3 whitespace-pre-wrap break-words font-sans text-sm text-muted">
          {job.source_text}
        </pre>
      </details>

      <details className="rounded-lg border border-border p-4 text-sm">
        <summary className="cursor-pointer text-danger">Hapus lowongan</summary>
        <p className="mt-2 text-muted">
          Lowongan dan hasil ekstraksinya dihapus permanen. Lamaran di tracker yang berasal dari
          lowongan ini tetap ada.
        </p>
        <form action={deleteJobPosting.bind(null, job.id)} className="mt-3">
          <button className="rounded-md bg-danger px-3 py-1.5 text-sm font-medium text-white hover:opacity-90">
            Ya, hapus permanen
          </button>
        </form>
      </details>
    </main>
  );
}

function Skills({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h2 className="font-medium text-muted">{title}</h2>
      {items.length === 0 ? (
        <p className="mt-1">Tidak disebut</p>
      ) : (
        <ul className="mt-1 flex flex-wrap gap-1.5">
          {items.map((s) => (
            <li key={s} className="rounded-full border border-border px-2 py-0.5">
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
