// Bentuk hasil POST /jobs/{id}/match dan kolom job_matches.result;
// harus sama dengan backend/app/matching.py dan app/match_api.py.
import type { EducationLevel } from "@/lib/jobs";
import type { Section } from "@/lib/profile";

export type Evidence = { entry_id: string; bullet_id: string | null };

export type SkillMatch = {
  skill: string;
  matched: boolean;
  method: "exact" | "text" | null;
  evidence: Evidence[];
};

export type EducationMatch = {
  required_level: EducationLevel | null;
  profile_level: EducationLevel | null;
  level_met: boolean;
  level_evidence: Evidence[];
  required_fields: string[];
  field_matched: string | null;
  field_evidence: Evidence[];
};

export type ExperienceMatch = {
  required_years: number | null;
  profile_years: number;
  evidence: Evidence[];
};

type Category<T> = { weight: number; score: number | null; detail: T };

export type MatchResult = {
  score: number | null;
  scorer_version: string;
  categories: {
    required_skills: Category<SkillMatch[]>;
    preferred_skills: Category<SkillMatch[]>;
    education: Category<EducationMatch>;
    experience: Category<ExperienceMatch>;
  };
  gaps: { required_skills: string[]; preferred_skills: string[] };
  sources: {
    entries: Record<string, { section: Section; title: string; organization: string | null }>;
    bullets: Record<string, string>;
  };
};

export const CATEGORY_LABELS: Record<keyof MatchResult["categories"], string> = {
  required_skills: "Skill wajib",
  preferred_skills: "Skill nilai tambah",
  education: "Pendidikan",
  experience: "Pengalaman",
};
