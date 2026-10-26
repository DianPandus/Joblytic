"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { educationLabel } from "@/lib/jobs";
import { CATEGORY_LABELS, type Evidence, type MatchResult, type SkillMatch } from "@/lib/matching";
import { sectionInfo } from "@/lib/profile";

type Response = MatchResult & { profile_entries: number };

// Snapshot tersimpan langsung ditampilkan, lalu skor dihitung ulang di backend
// supaya selalu mengikuti profil dan koreksi lowongan terbaru.
export function MatchPanel({ jobId, initial }: { jobId: string; initial: MatchResult | null }) {
  const [result, setResult] = useState<MatchResult | null>(initial);
  const [emptyProfile, setEmptyProfile] = useState(false);
  const [pending, setPending] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiFetch<Response>(`/jobs/${jobId}/match`, { method: "POST" })
      .then((data) => {
        if (cancelled) return;
        setResult(data);
        setEmptyProfile(data.profile_entries === 0);
      })
      .catch((err) => !cancelled && setError(err instanceof Error ? err.message : String(err)))
      .finally(() => !cancelled && setPending(false));
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  return (
    <section className="flex flex-col gap-4 rounded-lg border border-border bg-card p-4 text-sm">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-base font-medium">Kecocokan dengan profilmu</h2>
        {pending && <span className="text-xs text-muted">Menghitung ulang…</span>}
      </div>

      {error && (
        <p className="text-danger">
          Gagal menghitung skor: {error}
          {result && " Yang tampil adalah hasil terakhir yang tersimpan."}
        </p>
      )}
      {emptyProfile && (
        <p className="rounded-md border border-border p-3 text-muted">
          Profilmu masih kosong, jadi belum ada yang bisa dicocokkan.{" "}
          <Link href="/profile" className="text-accent underline">
            Unggah CV atau isi profil
          </Link>
          .
        </p>
      )}
      {!result && !error && <p className="text-muted">Menghitung skor…</p>}
      {result && <MatchDetail result={result} />}
    </section>
  );
}

function MatchDetail({ result }: { result: MatchResult }) {
  const { categories: c, sources } = result;
  return (
    <>
      <div>
        <p>
          <span className="text-4xl font-semibold">{result.score ?? "–"}</span>
          <span className="text-muted"> / 100</span>
        </p>
        <p className="mt-1 text-xs text-muted">
          Dihitung dari data profil dan persyaratan lowongan, tanpa AI. Skor ini alat bantu memilih
          prioritas, bukan prediksi peluang diterima.
        </p>
      </div>

      <ul className="flex flex-col gap-2">
        {(Object.keys(CATEGORY_LABELS) as (keyof typeof c)[]).map((key) => (
          <li key={key} className="grid grid-cols-[8.5rem_1fr_3rem] items-center gap-2">
            <span>
              {CATEGORY_LABELS[key]} <span className="text-xs text-muted">({c[key].weight})</span>
            </span>
            {c[key].score === null ? (
              <span className="col-span-2 text-xs text-muted">
                tidak disyaratkan, tidak dihitung
              </span>
            ) : (
              <>
                <span className="h-2 overflow-hidden rounded-full bg-border">
                  <span
                    className="block h-full rounded-full bg-accent"
                    style={{ width: `${Math.round(c[key].score * 100)}%` }}
                  />
                </span>
                <span className="text-right tabular-nums">{Math.round(c[key].score * 100)}%</span>
              </>
            )}
          </li>
        ))}
      </ul>

      <SkillList title="Skill wajib" matches={c.required_skills.detail} sources={sources} />
      <SkillList title="Skill nilai tambah" matches={c.preferred_skills.detail} sources={sources} />

      {c.education.score !== null && (
        <div>
          <h3 className="font-medium text-muted">Pendidikan</h3>
          <ul className="mt-1 space-y-0.5">
            {c.education.detail.required_level && (
              <li>
                {c.education.detail.level_met ? "✓" : "✗"} Diminta minimal{" "}
                {educationLabel(c.education.detail.required_level)}; di profil{" "}
                {educationLabel(c.education.detail.profile_level) ?? "tidak terbaca"}
                <Sources evidence={c.education.detail.level_evidence} sources={sources} />
              </li>
            )}
            {c.education.detail.required_fields.length > 0 && (
              <li>
                {c.education.detail.field_matched
                  ? `✓ Jurusan ${c.education.detail.field_matched} sesuai`
                  : `✗ Jurusan ${c.education.detail.required_fields.join(", ")} tidak ditemukan`}
                <Sources evidence={c.education.detail.field_evidence} sources={sources} />
              </li>
            )}
          </ul>
        </div>
      )}

      {c.experience.score !== null && (
        <div>
          <h3 className="font-medium text-muted">Pengalaman</h3>
          <p className="mt-1">
            Diminta {formatNumber(c.experience.detail.required_years ?? 0)} tahun; di profil{" "}
            {formatNumber(c.experience.detail.profile_years)} tahun (dari entri pengalaman kerja
            yang bertanggal)
          </p>
          <Sources evidence={c.experience.detail.evidence} sources={sources} />
        </div>
      )}
    </>
  );
}

function SkillList({
  title,
  matches,
  sources,
}: {
  title: string;
  matches: SkillMatch[];
  sources: MatchResult["sources"];
}) {
  if (matches.length === 0) return null;
  const found = matches.filter((m) => m.matched);
  const missing = matches.filter((m) => !m.matched);
  return (
    <div>
      <h3 className="font-medium text-muted">
        {title}{" "}
        <span className="text-xs">
          ({found.length}/{matches.length} ditemukan)
        </span>
      </h3>
      {found.length > 0 && (
        <ul className="mt-1 space-y-1">
          {found.map((m) => (
            <li key={m.skill}>
              <span className="rounded-full border border-accent px-2 py-0.5 text-accent">
                {m.skill}
              </span>
              <Sources evidence={m.evidence} sources={sources} />
            </li>
          ))}
        </ul>
      )}
      {missing.length > 0 && (
        <div className="mt-2">
          <p className="text-xs text-muted">Belum ditemukan di profil:</p>
          <ul className="mt-1 flex flex-wrap gap-1.5">
            {missing.map((m) => (
              <li
                key={m.skill}
                className="rounded-full border border-dashed border-danger px-2 py-0.5 text-danger"
              >
                {m.skill}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Sources({ evidence, sources }: { evidence: Evidence[]; sources: MatchResult["sources"] }) {
  if (evidence.length === 0) return null;
  return (
    <ul className="mt-0.5 space-y-0.5 pl-3 text-xs text-muted">
      {evidence.map((e) => {
        const entry = sources.entries[e.entry_id];
        if (!entry) return null;
        const bullet = e.bullet_id ? sources.bullets[e.bullet_id] : null;
        return (
          <li key={`${e.entry_id}:${e.bullet_id ?? ""}`}>
            {sectionInfo(entry.section).label}: {entry.title}
            {entry.organization ? ` · ${entry.organization}` : ""}
            {bullet && <> · “{bullet}”</>}
          </li>
        );
      })}
    </ul>
  );
}

function formatNumber(n: number): string {
  return String(n).replace(".", ",");
}
