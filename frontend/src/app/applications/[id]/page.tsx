import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import {
  addEvent,
  changeStage,
  deleteApplication,
  deleteEvent,
  updateApplication,
} from "@/app/applications/actions";
import { AppHeader } from "@/components/app-header";
import { ApplicationForm, inputClass } from "@/components/application-form";
import { EventForm } from "@/components/event-form";
import {
  type Application,
  type ApplicationEvent,
  STAGES,
  type StageHistoryEntry,
  eventKindLabel,
  formatDate,
  formatDateTime,
  isPast,
  stageLabel,
} from "@/lib/applications";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Detail lamaran · Joblytic" };

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export default async function ApplicationDetailPage(props: PageProps<"/applications/[id]">) {
  const { id } = await props.params;
  if (!UUID.test(id)) notFound();

  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  if (!claimsData?.claims) redirect(`/login?next=/applications/${id}`);

  // RLS: lamaran milik pengguna lain tidak akan ditemukan, jadi tampil 404.
  const [{ data: app }, { data: history }, { data: events }] = await Promise.all([
    supabase.from("applications").select("*").eq("id", id).maybeSingle(),
    supabase
      .from("application_stage_history")
      .select("id, from_stage, to_stage, changed_at")
      .eq("application_id", id)
      .order("changed_at", { ascending: false }),
    supabase
      .from("application_events")
      .select("id, application_id, kind, title, scheduled_at, notes")
      .eq("application_id", id)
      .order("scheduled_at"),
  ]);
  if (!app) notFound();

  const application = app as Application;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-10">
      <AppHeader active="/applications" />

      <section>
        <Link href="/applications" className="text-sm text-muted hover:text-foreground">
          ← Tracker
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{application.position}</h1>
        <p className="text-muted">
          {application.company}
          {application.location ? ` · ${application.location}` : ""}
        </p>
        {application.source_url && (
          <a
            href={application.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-1 inline-block break-all text-sm text-accent underline"
          >
            Lihat lowongan
          </a>
        )}
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-medium text-muted">Tahap</h2>
        <form
          action={changeStage.bind(null, application.id)}
          className="mt-2 flex flex-wrap items-center gap-3"
        >
          <select
            name="stage"
            defaultValue={application.stage}
            aria-label="Tahap lamaran"
            className={`${inputClass} w-auto`}
          >
            {STAGES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
          <button className="rounded-md bg-accent px-3 py-2 text-sm font-medium text-accent-foreground hover:opacity-90">
            Ubah tahap
          </button>
          <span className="text-sm text-muted">
            sejak {formatDateTime(application.stage_changed_at)}
          </span>
        </form>

        <h3 className="mt-4 text-sm font-medium text-muted">Riwayat</h3>
        <ol className="mt-2 space-y-1 text-sm">
          {((history ?? []) as StageHistoryEntry[]).map((h) => (
            <li key={h.id}>
              <span className="text-muted">{formatDateTime(h.changed_at)}</span>{" "}
              {h.from_stage
                ? `${stageLabel(h.from_stage)} → ${stageLabel(h.to_stage)}`
                : `Dibuat sebagai ${stageLabel(h.to_stage)}`}
            </li>
          ))}
        </ol>
      </section>

      <section className="rounded-lg border border-border bg-card p-4">
        <h2 className="text-sm font-medium text-muted">Jadwal</h2>
        {(events ?? []).length === 0 ? (
          <p className="mt-2 text-sm text-muted">Belum ada jadwal tes atau wawancara.</p>
        ) : (
          <ul className="mt-2 divide-y divide-border text-sm">
            {((events ?? []) as ApplicationEvent[]).map((ev) => {
              const past = isPast(ev.scheduled_at);
              return (
                <li key={ev.id} className="flex items-start justify-between gap-3 py-2">
                  <div className={past ? "text-muted" : undefined}>
                    <p>
                      <span className="font-medium">{ev.title}</span> ·{" "}
                      {eventKindLabel(ev.kind)}
                    </p>
                    <p className="text-muted">
                      {formatDateTime(ev.scheduled_at)} WIB{past ? " (lewat)" : ""}
                    </p>
                    {ev.notes && <p className="text-muted">{ev.notes}</p>}
                  </div>
                  <form action={deleteEvent.bind(null, application.id, ev.id)}>
                    <button className="text-xs text-danger hover:underline">Hapus</button>
                  </form>
                </li>
              );
            })}
          </ul>
        )}
        <div className="mt-4 border-t border-border pt-4">
          <EventForm action={addEvent.bind(null, application.id)} />
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium text-muted">Detail lamaran</h2>
        <ApplicationForm
          action={updateApplication.bind(null, application.id)}
          initial={application}
          submitLabel="Simpan perubahan"
        />
        <p className="mt-3 text-xs text-muted">
          Dibuat {formatDate(application.created_at)} · diperbarui{" "}
          {formatDateTime(application.updated_at)}
        </p>
      </section>

      <details className="rounded-lg border border-border p-4 text-sm">
        <summary className="cursor-pointer text-danger">Hapus lamaran</summary>
        <p className="mt-2 text-muted">
          Lamaran beserta riwayat tahap dan jadwalnya akan dihapus permanen.
        </p>
        <form action={deleteApplication.bind(null, application.id)} className="mt-3">
          <button className="rounded-md bg-danger px-3 py-1.5 text-sm font-medium text-white hover:opacity-90">
            Ya, hapus permanen
          </button>
        </form>
      </details>
    </main>
  );
}
