// Bagian profil; nilainya harus sama dengan check constraint di
// supabase/migrations/20261008000000_profile_cv.sql.
export const SECTIONS = [
  { value: "education", label: "Pendidikan", dated: true, orgLabel: "Institusi" },
  { value: "experience", label: "Pengalaman", dated: true, orgLabel: "Perusahaan" },
  { value: "organization", label: "Organisasi", dated: true, orgLabel: "Organisasi" },
  { value: "project", label: "Proyek", dated: true, orgLabel: "Klien/afiliasi" },
  { value: "certification", label: "Sertifikasi", dated: true, orgLabel: "Penerbit" },
  { value: "skill", label: "Skill", dated: false, orgLabel: null },
  { value: "language", label: "Bahasa", dated: false, orgLabel: null },
] as const;

export type Section = (typeof SECTIONS)[number]["value"];

export function isSection(value: unknown): value is Section {
  return SECTIONS.some((s) => s.value === value);
}

export function sectionInfo(section: Section) {
  return SECTIONS.find((s) => s.value === section)!;
}

export type ProfileBullet = { id: string; position: number; text: string };

export type ProfileEntry = {
  id: string;
  section: Section;
  title: string;
  organization: string | null;
  location: string | null;
  start_month: string | null;
  end_month: string | null;
  is_current: boolean;
  description: string | null;
  position: number;
  source: "cv" | "manual";
  profile_bullets: ProfileBullet[];
};

export type CvUpload = {
  file_name: string;
  status: "processing" | "done" | "failed";
  llm_model: string | null;
  created_at: string;
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

// start_month/end_month disimpan sebagai tanggal 1 (YYYY-MM-01).
export function formatMonth(value: string | null): string | null {
  if (!value) return null;
  const [y, m] = value.split("-");
  return `${MONTHS[Number(m) - 1]} ${y}`;
}

export function formatPeriod(e: Pick<ProfileEntry, "start_month" | "end_month" | "is_current">) {
  const start = formatMonth(e.start_month);
  const end = e.is_current ? "Sekarang" : formatMonth(e.end_month);
  if (start && end) return `${start} – ${end}`;
  return start ?? end ?? null;
}

export function toMarkdown(entries: ProfileEntry[]): string {
  const lines = ["# Profil", ""];
  for (const s of SECTIONS) {
    const items = entries.filter((e) => e.section === s.value);
    if (items.length === 0) continue;
    lines.push(`## ${s.label}`, "");
    if (!s.dated) {
      for (const e of items) {
        lines.push(`- ${e.title}${e.description ? ` (${e.description})` : ""}`);
      }
      lines.push("");
      continue;
    }
    for (const e of items) {
      const meta = [e.organization, e.location, formatPeriod(e)].filter(Boolean).join(" · ");
      lines.push(`### ${e.title}`);
      if (meta) lines.push(meta);
      if (e.description) lines.push("", e.description);
      if (e.profile_bullets.length) {
        lines.push("");
        for (const b of e.profile_bullets) lines.push(`- ${b.text}`);
      }
      lines.push("");
    }
  }
  return lines.join("\n");
}
