import Link from "next/link";
import { redirect } from "next/navigation";
import { AppHeader } from "@/components/app-header";
import { JobPaste } from "@/components/job-paste";
import { formatDate } from "@/lib/applications";
import { type JobPosting, jobTitle } from "@/lib/jobs";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Lowongan · Joblytic" };

type Row = Pick<
  JobPosting,
  "id" | "position" | "company" | "location" | "required_skills" | "corrected_at" | "created_at"
> & {
  applications: { id: string }[];
  // PostgREST bisa mengembalikan relasi ini sebagai objek atau array.
  job_matches: { score: number | null } | { score: number | null }[] | null;
};

function matchScore(job: Row): number | null {
  return [job.job_matches].flat()[0]?.score ?? null;
}

export default async function JobsPage() {
  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  if (!claimsData?.claims) redirect("/login?next=/jobs");

  const { data, error } = await supabase
    .from("job_postings")
    .select(
      "id, position, company, location, required_skills, corrected_at, created_at, applications(id), job_matches(score)",
    )
    .order("created_at", { ascending: false });
  const jobs = (data ?? []) as Row[];

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-10">
      <AppHeader active="/jobs" />

      <section>
        <h1 className="text-2xl font-semibold">Lowongan</h1>
        <p className="mt-1 text-sm text-muted">
          Tempel lowongan untuk membaca persyaratannya otomatis. Lowongan yang sama tidak
          dianalisis dua kali.
        </p>
      </section>

      <JobPaste />

      <section>
        <h2 className="mb-2 font-medium">
          Tersimpan <span className="text-sm text-muted">({jobs.length})</span>
        </h2>
        {error && <p className="text-sm text-danger">Gagal memuat lowongan. Coba muat ulang.</p>}
        {!error && jobs.length === 0 ? (
          <p className="text-sm text-muted">Belum ada lowongan yang dianalisis.</p>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border bg-card">
            {jobs.map((job) => (
              <li key={job.id}>
                <Link href={`/jobs/${job.id}`} className="block p-4 hover:bg-background">
                  <div className="flex items-baseline justify-between gap-3">
                    <p className="font-medium">{jobTitle(job)}</p>
                    {matchScore(job) !== null && (
                      <span className="shrink-0 text-sm tabular-nums text-accent">
                        {matchScore(job)}/100
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted">
                    {[
                      job.location,
                      `${job.required_skills.length} skill wajib`,
                      `dianalisis ${formatDate(job.created_at)}`,
                    ]
                      .filter(Boolean)
                      .join(" · ")}
                  </p>
                  {(job.corrected_at || job.applications.length > 0) && (
                    <p className="mt-1 flex gap-2 text-xs">
                      {job.corrected_at && (
                        <span className="rounded-full border border-border px-2 py-0.5 text-muted">
                          dikoreksi
                        </span>
                      )}
                      {job.applications.length > 0 && (
                        <span className="rounded-full border border-accent px-2 py-0.5 text-accent">
                          di tracker
                        </span>
                      )}
                    </p>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
