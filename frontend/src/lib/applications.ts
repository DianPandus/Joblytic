// Tahap lamaran; urutan dan nilainya harus sama dengan check constraint di
// supabase/migrations/20261007000000_applications_tracker.sql.
export const STAGES = [
  { value: "prepared", label: "Disiapkan" },
  { value: "submitted", label: "Dikirim" },
  { value: "assessment", label: "Tes/Asesmen" },
  { value: "interview", label: "Wawancara" },
  { value: "offer", label: "Penawaran" },
  { value: "rejected", label: "Ditolak" },
  { value: "closed", label: "Ditutup" },
] as const;

export type Stage = (typeof STAGES)[number]["value"];

export const EVENT_KINDS = [
  { value: "assessment", label: "Tes/Asesmen" },
  { value: "interview", label: "Wawancara" },
  { value: "other", label: "Lainnya" },
] as const;

export type EventKind = (typeof EVENT_KINDS)[number]["value"];

export function isStage(value: unknown): value is Stage {
  return STAGES.some((s) => s.value === value);
}

export function isEventKind(value: unknown): value is EventKind {
  return EVENT_KINDS.some((k) => k.value === value);
}

export function stageLabel(stage: string): string {
  return STAGES.find((s) => s.value === stage)?.label ?? stage;
}

export function eventKindLabel(kind: string): string {
  return EVENT_KINDS.find((k) => k.value === kind)?.label ?? kind;
}

export type Application = {
  id: string;
  company: string;
  position: string;
  location: string | null;
  source_url: string | null;
  applied_at: string | null;
  stage: Stage;
  stage_changed_at: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type StageHistoryEntry = {
  id: number;
  from_stage: Stage | null;
  to_stage: Stage;
  changed_at: string;
};

export type ApplicationEvent = {
  id: string;
  application_id: string;
  kind: EventKind;
  title: string;
  scheduled_at: string;
  notes: string | null;
};

export function formatDate(value: string | null): string {
  if (!value) return "-";
  // Kolom `date` (YYYY-MM-DD) tidak punya zona waktu, jadi diformat apa adanya di UTC
  // agar tanggalnya tidak bergeser; timestamp diformat di WIB.
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
  return new Date(dateOnly ? `${value}T00:00:00Z` : value).toLocaleDateString("id-ID", {
    dateStyle: "medium",
    timeZone: dateOnly ? "UTC" : "Asia/Jakarta",
  });
}

export function isPast(value: string): boolean {
  return new Date(value).getTime() < Date.now();
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Asia/Jakarta",
  });
}
