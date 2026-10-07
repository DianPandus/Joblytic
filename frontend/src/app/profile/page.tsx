import { redirect } from "next/navigation";
import { deleteEntry, saveEntry } from "@/app/profile/actions";
import { AppHeader } from "@/components/app-header";
import { CvUpload } from "@/components/cv-upload";
import { EntryForm } from "@/components/entry-form";
import { formatDateTime } from "@/lib/applications";
import {
  type CvUpload as CvUploadRow,
  type ProfileEntry,
  SECTIONS,
  formatPeriod,
} from "@/lib/profile";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Profil · Joblytic" };

export default async function ProfilePage() {
  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  if (!claimsData?.claims) redirect("/login?next=/profile");

  // RLS membatasi hasil ke data milik pengguna sendiri.
  const [{ data: entryRows, error }, { data: uploads }] = await Promise.all([
    supabase
      .from("profile_entries")
      .select(
        "id, section, title, organization, location, start_month, end_month, is_current, description, position, source, profile_bullets(id, position, text)",
      )
      .order("position")
      .order("position", { referencedTable: "profile_bullets" }),
    supabase
      .from("cv_uploads")
      .select("file_name, status, llm_model, created_at")
      .eq("status", "done")
      .order("created_at", { ascending: false })
      .limit(1),
  ]);
  const entries = (entryRows ?? []) as ProfileEntry[];
  const lastUpload = (uploads?.[0] ?? null) as CvUploadRow | null;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-10">
      <AppHeader active="/profile" />

      <section className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Profil</h1>
          <p className="mt-1 text-sm text-muted">
            Sumber data untuk skor kecocokan dan saran CV. Hanya isi yang benar-benar kamu
            punya; bagian yang kosong biarkan kosong.
          </p>
          {lastUpload && (
            <p className="mt-1 text-xs text-muted">
              Terakhir diisi dari {lastUpload.file_name} · {formatDateTime(lastUpload.created_at)}
              {lastUpload.llm_model ? ` · ${lastUpload.llm_model}` : ""}
            </p>
          )}
        </div>
        {entries.length > 0 && (
          <a
            href="/profile/export"
            className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-card"
          >
            Ekspor Markdown
          </a>
        )}
      </section>

      <CvUpload hasEntries={entries.length > 0} />

      {error && <p className="text-sm text-danger">Gagal memuat profil. Coba muat ulang.</p>}

      {SECTIONS.map((s) => {
        const items = entries.filter((e) => e.section === s.value);
        return (
          <section key={s.value}>
            <h2 className="mb-2 font-medium">
              {s.label} <span className="text-sm text-muted">({items.length})</span>
            </h2>
            {items.length === 0 ? (
              <p className="text-sm text-muted">Belum ada.</p>
            ) : (
              <ul className="divide-y divide-border rounded-lg border border-border bg-card">
                {items.map((e) => (
                  <li key={e.id} className="p-4">
                    <EntrySummary entry={e} />
                    <details className="mt-2">
                      <summary className="cursor-pointer text-sm text-accent">Edit</summary>
                      <div className="mt-3">
                        <EntryForm
                          section={e.section}
                          entry={e}
                          action={saveEntry.bind(null, e.id, e.section)}
                        />
                        <form action={deleteEntry.bind(null, e.id)} className="mt-3">
                          <button className="text-sm text-danger hover:underline">
                            Hapus entri ini
                          </button>
                        </form>
                      </div>
                    </details>
                  </li>
                ))}
              </ul>
            )}
            <details className="mt-2">
              <summary className="cursor-pointer text-sm text-muted hover:text-foreground">
                + Tambah {s.label.toLowerCase()}
              </summary>
              <div className="mt-3 rounded-lg border border-border p-4">
                <EntryForm section={s.value} action={saveEntry.bind(null, null, s.value)} />
              </div>
            </details>
          </section>
        );
      })}
    </main>
  );
}

function EntrySummary({ entry: e }: { entry: ProfileEntry }) {
  const meta = [e.organization, e.location, formatPeriod(e)].filter(Boolean).join(" · ");
  return (
    <div className="text-sm">
      <p className="font-medium">
        {e.title}
        {e.source === "manual" && (
          <span className="ml-2 rounded-full border border-border px-2 py-0.5 text-xs font-normal text-muted">
            manual
          </span>
        )}
      </p>
      {meta && <p className="text-muted">{meta}</p>}
      {e.description && <p className="text-muted">{e.description}</p>}
      {e.profile_bullets.length > 0 && (
        <ul className="mt-1 list-disc pl-5">
          {e.profile_bullets.map((b) => (
            <li key={b.id}>{b.text}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
