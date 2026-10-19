"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import type { FormState } from "@/app/applications/actions";
import { ValidationError, httpUrl, lines, text } from "@/lib/form";
import { isEducationLevel } from "@/lib/jobs";
import { createClient } from "@/lib/supabase/server";

// Server Action bisa dipanggil langsung lewat POST, jadi setiap action memeriksa
// login sendiri. Kepemilikan data tetap ditegakkan RLS di database.
async function requireUser() {
  const supabase = await createClient();
  const { data } = await supabase.auth.getClaims();
  if (!data?.claims) redirect("/login?next=/jobs");
  return supabase;
}

function years(form: FormData): number | null {
  const value = text(form, "min_experience_years", 5);
  if (!value) return null;
  const n = Number(value.replace(",", "."));
  if (!Number.isFinite(n) || n < 0 || n > 50) {
    throw new ValidationError("Pengalaman minimal harus angka 0-50 tahun.");
  }
  return Math.round(n * 2) / 2;
}

function jobFields(form: FormData) {
  const level = String(form.get("education_level") ?? "");
  const required = lines(form, "required_skills", 60, 100);
  const requiredKeys = new Set(required.map((s) => s.toLowerCase()));
  return {
    position: text(form, "position", 200),
    company: text(form, "company", 200),
    location: text(form, "location", 200),
    source_url: httpUrl(form, "source_url"),
    required_skills: required,
    // Skill yang sudah wajib tidak dihitung dua kali sebagai nilai tambah.
    preferred_skills: lines(form, "preferred_skills", 60, 100).filter(
      (s) => !requiredKeys.has(s.toLowerCase()),
    ),
    education_level: isEducationLevel(level) ? level : null,
    education_fields: lines(form, "education_fields", 30, 200),
    min_experience_years: years(form),
    responsibilities: lines(form, "responsibilities", 40, 1000),
  };
}

export async function updateJobPosting(
  id: string,
  _prev: FormState,
  form: FormData,
): Promise<FormState> {
  const supabase = await requireUser();
  let fields;
  try {
    fields = jobFields(form);
  } catch (e) {
    if (e instanceof ValidationError) return { error: e.message };
    throw e;
  }

  // Kolom `extracted` tidak diubah, jadi keluaran asli pipeline tetap bisa dibandingkan.
  const { error } = await supabase
    .from("job_postings")
    .update({ ...fields, corrected_at: new Date().toISOString() })
    .eq("id", id);
  if (error) return { error: "Gagal menyimpan koreksi. Coba lagi." };

  revalidatePath("/jobs");
  revalidatePath(`/jobs/${id}`);
  return { ok: true };
}

// Simpan lowongan sebagai lamaran baru di tracker (tahap Disiapkan).
export async function createApplicationFromJob(id: string) {
  const supabase = await requireUser();
  const { data: job } = await supabase
    .from("job_postings")
    .select("id, position, company, location, source_url")
    .eq("id", id)
    .maybeSingle();
  if (!job) throw new Error("Lowongan tidak ditemukan");

  const { data: existing } = await supabase
    .from("applications")
    .select("id")
    .eq("job_posting_id", id)
    .limit(1)
    .maybeSingle();
  if (existing) redirect(`/applications/${existing.id}`);

  const { data, error } = await supabase
    .from("applications")
    .insert({
      // Tracker mewajibkan perusahaan dan posisi; isian kosong bisa dilengkapi di sana.
      company: job.company ?? "Perusahaan belum diisi",
      position: job.position ?? "Posisi belum diisi",
      location: job.location,
      source_url: job.source_url,
      job_posting_id: job.id,
      stage: "prepared",
    })
    .select("id")
    .single();
  if (error) throw new Error("Gagal menyimpan lamaran");

  revalidatePath("/applications");
  revalidatePath(`/jobs/${id}`);
  redirect(`/applications/${data.id}`);
}

export async function deleteJobPosting(id: string) {
  const supabase = await requireUser();
  // Lamaran yang tertaut tetap ada; tautannya dilepas oleh foreign key di database.
  const { error } = await supabase.from("job_postings").delete().eq("id", id);
  if (error) throw new Error("Gagal menghapus lowongan");

  revalidatePath("/jobs");
  redirect("/jobs");
}
