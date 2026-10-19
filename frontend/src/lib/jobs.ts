// Jenjang pendidikan; nilainya harus sama dengan check constraint di
// supabase/migrations/20261009000000_job_postings.sql dan EducationLevel di backend.
export const EDUCATION_LEVELS = [
  { value: "sma", label: "SMA/SMK" },
  { value: "d3", label: "D3" },
  { value: "d4", label: "D4" },
  { value: "s1", label: "S1" },
  { value: "s2", label: "S2" },
  { value: "s3", label: "S3" },
] as const;

export type EducationLevel = (typeof EDUCATION_LEVELS)[number]["value"];

export function isEducationLevel(value: unknown): value is EducationLevel {
  return EDUCATION_LEVELS.some((l) => l.value === value);
}

export function educationLabel(level: string | null): string | null {
  return level ? (EDUCATION_LEVELS.find((l) => l.value === level)?.label ?? level) : null;
}

export type JobPosting = {
  id: string;
  source_text: string;
  source_url: string | null;
  position: string | null;
  company: string | null;
  location: string | null;
  required_skills: string[];
  preferred_skills: string[];
  education_level: EducationLevel | null;
  education_fields: string[];
  min_experience_years: number | null;
  responsibilities: string[];
  llm_model: string | null;
  prompt_version: string | null;
  corrected_at: string | null;
  created_at: string;
};

export function jobTitle(job: Pick<JobPosting, "position" | "company">): string {
  return [job.position ?? "Posisi tanpa nama", job.company].filter(Boolean).join(" · ");
}

export function formatYears(years: number | null): string | null {
  if (years === null) return null;
  if (years === 0) return "Fresh graduate dipersilakan";
  return `Minimal ${String(years).replace(".", ",")} tahun`;
}
