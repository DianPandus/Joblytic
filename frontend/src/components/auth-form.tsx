"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { safeNext } from "@/lib/safe-next";
import { createClient } from "@/lib/supabase/client";

type Mode = "login" | "signup";

const inputClass =
  "w-full rounded-md border border-border bg-card px-3 py-2 outline-none focus:border-accent";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(
    searchParams.get("error") ? "Tautan konfirmasi tidak valid atau kedaluwarsa." : null,
  );

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setNotice(null);

    const form = new FormData(e.currentTarget);
    const email = String(form.get("email"));
    const password = String(form.get("password"));
    const supabase = createClient();

    if (mode === "signup") {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { full_name: String(form.get("full_name") ?? "") },
          emailRedirectTo: `${window.location.origin}/auth/confirm`,
        },
      });
      setLoading(false);
      if (error) return setError(error.message);
      if (!data.session) {
        return setNotice("Cek email kamu untuk mengonfirmasi akun, lalu masuk.");
      }
    } else {
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      setLoading(false);
      if (error) return setError(error.message);
    }

    router.replace(safeNext(searchParams.get("next")));
    router.refresh();
  }

  const isSignup = mode === "signup";

  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 px-4 py-16">
      <div>
        <Link href="/" className="font-mono text-sm text-accent">
          Joblytic
        </Link>
        <h1 className="mt-2 text-2xl font-semibold">{isSignup ? "Buat akun" : "Masuk"}</h1>
      </div>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        {isSignup && (
          <label className="flex flex-col gap-1 text-sm">
            Nama
            <input name="full_name" autoComplete="name" className={inputClass} />
          </label>
        )}
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input name="email" type="email" required autoComplete="email" className={inputClass} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Password
          <input
            name="password"
            type="password"
            required
            minLength={8}
            autoComplete={isSignup ? "new-password" : "current-password"}
            className={inputClass}
          />
        </label>

        {error && <p className="text-sm text-danger">{error}</p>}
        {notice && <p className="text-sm text-accent">{notice}</p>}

        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-accent px-4 py-2 font-medium text-accent-foreground hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Memproses…" : isSignup ? "Daftar" : "Masuk"}
        </button>
      </form>

      <p className="text-sm text-muted">
        {isSignup ? "Sudah punya akun? " : "Belum punya akun? "}
        <Link href={isSignup ? "/login" : "/signup"} className="text-accent underline">
          {isSignup ? "Masuk" : "Daftar"}
        </Link>
      </p>
    </main>
  );
}
