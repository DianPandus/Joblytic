import Link from "next/link";
import { redirect } from "next/navigation";
import { createApplication } from "@/app/applications/actions";
import { AppHeader } from "@/components/app-header";
import { ApplicationForm } from "@/components/application-form";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Tambah lamaran · Joblytic" };

export default async function NewApplicationPage() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims) redirect("/login?next=/applications/new");

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-10">
      <AppHeader active="/applications" />
      <div>
        <Link href="/applications" className="text-sm text-muted hover:text-foreground">
          ← Tracker
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">Tambah lamaran</h1>
      </div>
      <ApplicationForm action={createApplication} submitLabel="Simpan lamaran" />
    </main>
  );
}
