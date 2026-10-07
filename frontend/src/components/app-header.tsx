import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

async function signOut() {
  "use server";
  const supabase = await createClient();
  await supabase.auth.signOut();
  redirect("/login");
}

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/applications", label: "Tracker" },
] as const;

export function AppHeader({ active }: { active: (typeof NAV)[number]["href"] }) {
  return (
    <header className="flex items-center justify-between gap-4">
      <nav className="flex items-center gap-4 text-sm">
        <span className="font-mono text-accent">Joblytic</span>
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={item.href === active ? "font-medium" : "text-muted hover:text-foreground"}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <form action={signOut}>
        <button className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-card">
          Keluar
        </button>
      </form>
    </header>
  );
}
