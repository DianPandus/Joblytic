import Link from "next/link";
import { redirect } from "next/navigation";
import { AppHeader } from "@/components/app-header";
import { type Application, STAGES, formatDate, isStage, stageLabel } from "@/lib/applications";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Tracker · Joblytic" };

export default async function ApplicationsPage(props: PageProps<"/applications">) {
  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  if (!claimsData?.claims) redirect("/login?next=/applications");

  const { stage } = await props.searchParams;
  const activeStage = isStage(stage) ? stage : null;

  // RLS membatasi hasil ke lamaran milik pengguna sendiri.
  const { data, error } = await supabase
    .from("applications")
    .select("*")
    .order("updated_at", { ascending: false });
  const applications = (data ?? []) as Application[];

  const counts = new Map<string, number>();
  for (const a of applications) counts.set(a.stage, (counts.get(a.stage) ?? 0) + 1);
  const visible = activeStage
    ? applications.filter((a) => a.stage === activeStage)
    : applications;

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-4 py-10">
      <AppHeader active="/applications" />

      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Tracker lamaran</h1>
          <p className="mt-1 text-sm text-muted">{applications.length} lamaran tercatat.</p>
        </div>
        <Link
          href="/applications/new"
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-accent-foreground hover:opacity-90"
        >
          Tambah lamaran
        </Link>
      </section>

      <nav className="flex flex-wrap gap-2 text-sm" aria-label="Filter tahap">
        <StageChip href="/applications" active={!activeStage}>
          Semua ({applications.length})
        </StageChip>
        {STAGES.map((s) => (
          <StageChip
            key={s.value}
            href={`/applications?stage=${s.value}`}
            active={activeStage === s.value}
          >
            {s.label} ({counts.get(s.value) ?? 0})
          </StageChip>
        ))}
      </nav>

      {error ? (
        <p className="text-sm text-danger">Gagal memuat lamaran. Coba muat ulang halaman.</p>
      ) : visible.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted">
          {applications.length === 0
            ? "Belum ada lamaran. Mulai dengan menambahkan lamaran pertamamu."
            : "Tidak ada lamaran di tahap ini."}
        </p>
      ) : (
        <ul className="divide-y divide-border rounded-lg border border-border bg-card">
          {visible.map((a) => (
            <li key={a.id}>
              <Link
                href={`/applications/${a.id}`}
                className="flex flex-wrap items-center justify-between gap-2 p-4 hover:bg-background"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{a.position}</p>
                  <p className="truncate text-sm text-muted">
                    {a.company}
                    {a.location ? ` · ${a.location}` : ""}
                  </p>
                </div>
                <div className="text-right text-sm">
                  <span className="rounded-full border border-border px-2 py-0.5">
                    {stageLabel(a.stage)}
                  </span>
                  <p className="mt-1 text-xs text-muted">
                    Dilamar {formatDate(a.applied_at)} · tahap sejak{" "}
                    {formatDate(a.stage_changed_at)}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function StageChip({
  href,
  active,
  children,
}: {
  href: string;
  active: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      aria-current={active ? "page" : undefined}
      className={
        active
          ? "rounded-full bg-accent px-3 py-1 text-accent-foreground"
          : "rounded-full border border-border px-3 py-1 text-muted hover:text-foreground"
      }
    >
      {children}
    </Link>
  );
}
