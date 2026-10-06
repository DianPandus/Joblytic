import { redirect } from "next/navigation";
import { BackendStatus } from "@/components/backend-status";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Dashboard · Joblytic" };

async function signOut() {
  "use server";
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}

export default async function DashboardPage() {
  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  const claims = claimsData?.claims;
  if (!claims) redirect("/login?next=/dashboard");

  // RLS memastikan query ini hanya bisa mengembalikan baris milik pengguna sendiri.
  const { data: profile } = await supabase
    .from("profiles")
    .select("email, full_name, role, created_at")
    .eq("id", claims.sub)
    .maybeSingle();

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-8 px-4 py-10">
      <header className="flex items-center justify-between gap-4">
        <span className="font-mono text-sm text-accent">Joblytic</span>
        <form action={signOut}>
          <button className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-card">
            Keluar
          </button>
        </form>
      </header>

      <section>
        <h1 className="text-2xl font-semibold">
          Halo, {profile?.full_name || profile?.email || claims.email}
        </h1>
        <p className="mt-1 text-muted">
          Fitur profil, analisis lowongan, dan tracker lamaran akan muncul di sini.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-lg border border-border bg-card p-4">
          <h2 className="text-sm font-medium text-muted">Akun (dari database)</h2>
          {profile ? (
            <dl className="mt-2 space-y-1 text-sm">
              <div>
                <dt className="inline text-muted">Email: </dt>
                <dd className="inline">{profile.email}</dd>
              </div>
              <div>
                <dt className="inline text-muted">Peran: </dt>
                <dd className="inline">{profile.role}</dd>
              </div>
              <div>
                <dt className="inline text-muted">Terdaftar: </dt>
                <dd className="inline">
                  {new Date(profile.created_at).toLocaleDateString("id-ID", {
                    dateStyle: "long",
                  })}
                </dd>
              </div>
            </dl>
          ) : (
            <p className="mt-2 text-sm text-danger">Profil belum ditemukan di database.</p>
          )}
        </div>
        <BackendStatus />
      </section>
    </main>
  );
}
