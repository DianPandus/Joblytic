"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { isEventKind, isStage } from "@/lib/applications";
import { createClient } from "@/lib/supabase/server";

export type FormState = { error?: string; ok?: boolean };

// Server Action bisa dipanggil langsung lewat POST, jadi setiap action memeriksa
// login sendiri. Kepemilikan data tetap ditegakkan RLS di database.
async function requireUser() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims) redirect("/login?next=/applications");
  return supabase;
}

function text(form: FormData, name: string, max: number): string | null {
  const value = String(form.get(name) ?? "").trim();
  if (!value) return null;
  if (value.length > max) throw new ValidationError(`Isian "${name}" terlalu panjang.`);
  return value;
}

function httpUrl(form: FormData, name: string): string | null {
  const value = text(form, name, 2000);
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol === "http:" || url.protocol === "https:") return url.toString();
  } catch {}
  throw new ValidationError("Tautan harus berupa URL http:// atau https://.");
}

function isoDate(form: FormData, name: string): string | null {
  const value = text(form, name, 10);
  if (!value) return null;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) throw new ValidationError("Format tanggal tidak valid.");
  return value;
}

class ValidationError extends Error {}

function applicationFields(form: FormData) {
  const company = text(form, "company", 200);
  const position = text(form, "position", 200);
  if (!company || !position) throw new ValidationError("Perusahaan dan posisi wajib diisi.");
  return {
    company,
    position,
    location: text(form, "location", 200),
    source_url: httpUrl(form, "source_url"),
    applied_at: isoDate(form, "applied_at"),
    notes: text(form, "notes", 10000),
  };
}

export async function createApplication(_prev: FormState, form: FormData): Promise<FormState> {
  const supabase = await requireUser();
  let fields;
  try {
    fields = applicationFields(form);
  } catch (e) {
    if (e instanceof ValidationError) return { error: e.message };
    throw e;
  }
  const stage = form.get("stage");

  const { data, error } = await supabase
    .from("applications")
    .insert({ ...fields, stage: isStage(stage) ? stage : "prepared" })
    .select("id")
    .single();
  if (error) return { error: "Gagal menyimpan lamaran. Coba lagi." };

  revalidatePath("/applications");
  redirect(`/applications/${data.id}`);
}

export async function updateApplication(
  id: string,
  _prev: FormState,
  form: FormData,
): Promise<FormState> {
  const supabase = await requireUser();
  let fields;
  try {
    fields = applicationFields(form);
  } catch (e) {
    if (e instanceof ValidationError) return { error: e.message };
    throw e;
  }

  const { error } = await supabase.from("applications").update(fields).eq("id", id);
  if (error) return { error: "Gagal menyimpan perubahan. Coba lagi." };

  revalidatePath("/applications");
  revalidatePath(`/applications/${id}`);
  return { ok: true };
}

export async function changeStage(id: string, form: FormData) {
  const supabase = await requireUser();
  const stage = form.get("stage");
  if (!isStage(stage)) throw new Error("Tahap tidak dikenal");

  // Riwayat tahap dan stage_changed_at diisi trigger di database.
  const { error } = await supabase.from("applications").update({ stage }).eq("id", id);
  if (error) throw new Error("Gagal mengubah tahap");

  revalidatePath("/applications");
  revalidatePath(`/applications/${id}`);
}

export async function deleteApplication(id: string) {
  const supabase = await requireUser();
  const { error } = await supabase.from("applications").delete().eq("id", id);
  if (error) throw new Error("Gagal menghapus lamaran");

  revalidatePath("/applications");
  redirect("/applications");
}

export async function addEvent(
  applicationId: string,
  _prev: FormState,
  form: FormData,
): Promise<FormState> {
  const supabase = await requireUser();
  const kind = form.get("kind");
  let title, notes;
  try {
    title = text(form, "title", 200);
    notes = text(form, "notes", 2000);
  } catch (e) {
    if (e instanceof ValidationError) return { error: e.message };
    throw e;
  }
  const when = String(form.get("scheduled_at") ?? "");
  if (!isEventKind(kind) || !title) return { error: "Jenis dan judul jadwal wajib diisi." };
  // <input type="datetime-local"> tidak membawa zona waktu; pengguna di Indonesia (WIB).
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(when)) return { error: "Waktu jadwal tidak valid." };

  const { error } = await supabase.from("application_events").insert({
    application_id: applicationId,
    kind,
    title,
    notes,
    scheduled_at: `${when}:00+07:00`,
  });
  if (error) return { error: "Gagal menyimpan jadwal. Coba lagi." };

  revalidatePath(`/applications/${applicationId}`);
  return { ok: true };
}

export async function deleteEvent(applicationId: string, eventId: string) {
  const supabase = await requireUser();
  const { error } = await supabase.from("application_events").delete().eq("id", eventId);
  if (error) throw new Error("Gagal menghapus jadwal");

  revalidatePath(`/applications/${applicationId}`);
}
