import { type ProfileEntry, toMarkdown } from "@/lib/profile";
import { createClient } from "@/lib/supabase/server";

// Ekspor profil ke Markdown (PRD US-1).
export async function GET() {
  const supabase = await createClient();
  const { data: claimsData } = await supabase.auth.getClaims();
  if (!claimsData?.claims) return new Response("Butuh login", { status: 401 });

  const { data, error } = await supabase
    .from("profile_entries")
    .select(
      "id, section, title, organization, location, start_month, end_month, is_current, description, position, source, profile_bullets(id, position, text)",
    )
    .order("position")
    .order("position", { referencedTable: "profile_bullets" });
  if (error) return new Response("Gagal memuat profil", { status: 500 });

  return new Response(toMarkdown((data ?? []) as ProfileEntry[]), {
    headers: {
      "Content-Type": "text/markdown; charset=utf-8",
      "Content-Disposition": 'attachment; filename="profil-joblytic.md"',
      "Cache-Control": "no-store",
    },
  });
}
