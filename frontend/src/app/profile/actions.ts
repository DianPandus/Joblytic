"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import type { FormState } from "@/app/applications/actions";
import { isSection } from "@/lib/profile";
import { createClient } from "@/lib/supabase/server";

// Server Action bisa dipanggil langsung lewat POST: cek login di setiap action.
// Kepemilikan entri tetap ditegakkan RLS di database.
async function requireUser() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims) redirect("/login?next=/profile");
  return supabase;
}

function text(form: FormData, name: string, max: number): string | null {
  const value = String(form.get(name) ?? "").trim();
  return value ? value.slice(0, max) : null;
}

// <input type="month"> mengirim "YYYY-MM"; database menyimpan tanggal 1 bulan itu.
function month(form: FormData, name: string): string | null {
  const value = String(form.get(name) ?? "");
  return /^\d{4}-(0[1-9]|1[0-2])$/.test(value) ? `${value}-01` : null;
}

export async function saveEntry(
  entryId: string | null,
  section: string,
  _prev: FormState,
  form: FormData,
): Promise<FormState> {
  const supabase = await requireUser();
  if (!isSection(section)) return { error: "Bagian profil tidak dikenal." };

  const title = text(form, "title", 300);
  if (!title) return { error: "Judul wajib diisi." };
  const isCurrent = form.get("is_current") === "on";
  const start = month(form, "start_month");
  let end = isCurrent ? null : month(form, "end_month");
  if (start && end && end < start) end = null;

  const fields = {
    title,
    organization: text(form, "organization", 300),
    location: text(form, "location", 200),
    start_month: start,
    end_month: end,
    is_current: isCurrent,
    description: text(form, "description", 2000),
  };

  let id = entryId;
  if (id) {
    const { error } = await supabase.from("profile_entries").update(fields).eq("id", id);
    if (error) return { error: "Gagal menyimpan. Coba lagi." };
  } else {
    // Entri manual ditaruh di akhir bagiannya.
    const { data: last } = await supabase
      .from("profile_entries")
      .select("position")
      .eq("section", section)
      .order("position", { ascending: false })
      .limit(1)
      .maybeSingle();
    const { data, error } = await supabase
      .from("profile_entries")
      .insert({ ...fields, section, position: (last?.position ?? -1) + 1, source: "manual" })
      .select("id")
      .single();
    if (error) return { error: "Gagal menyimpan. Coba lagi." };
    id = data.id as string;
  }

  const bullets = String(form.get("bullets") ?? "")
    .split("\n")
    .map((b) => b.trim().slice(0, 1000))
    .filter(Boolean)
    .slice(0, 30);
  const error = await syncBullets(supabase, id, bullets);
  if (error) return { error };

  revalidatePath("/profile");
  return { ok: true };
}

// Perbarui butir di tempat menurut urutan, supaya ID butir yang tidak berubah tetap
// sama (dirujuk oleh saran CV di Fase 4); sisanya ditambah atau dihapus.
async function syncBullets(
  supabase: Awaited<ReturnType<typeof createClient>>,
  entryId: string,
  bullets: string[],
): Promise<string | null> {
  const { data: existing, error } = await supabase
    .from("profile_bullets")
    .select("id, position, text")
    .eq("entry_id", entryId)
    .order("position");
  if (error) return "Gagal memuat butir.";

  for (let i = 0; i < bullets.length; i++) {
    const current = existing[i];
    const res = current
      ? current.text === bullets[i] && current.position === i
        ? null
        : await supabase
            .from("profile_bullets")
            .update({ text: bullets[i], position: i })
            .eq("id", current.id)
      : await supabase
          .from("profile_bullets")
          .insert({ entry_id: entryId, position: i, text: bullets[i] });
    if (res?.error) return "Gagal menyimpan butir.";
  }

  const extra = existing.slice(bullets.length).map((b) => b.id);
  if (extra.length) {
    const { error: delError } = await supabase.from("profile_bullets").delete().in("id", extra);
    if (delError) return "Gagal menghapus butir.";
  }
  return null;
}

export async function deleteEntry(entryId: string) {
  const supabase = await requireUser();
  const { error } = await supabase.from("profile_entries").delete().eq("id", entryId);
  if (error) throw new Error("Gagal menghapus entri");
  revalidatePath("/profile");
}
