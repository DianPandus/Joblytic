import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-8 px-4 py-16">
      <p className="font-mono text-sm text-accent">Joblytic</p>
      <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
        Kelola semua lamaran kerja di satu tempat.
      </h1>
      <p className="max-w-xl text-lg text-muted">
        Nilai kecocokan CV dengan lowongan, lihat gap skill, dapatkan saran CV yang tetap jujur
        pada pengalamanmu, dan lacak setiap tahap seleksi.
      </p>
      <div className="flex flex-wrap gap-3">
        <Link
          href="/signup"
          className="rounded-md bg-accent px-5 py-2.5 font-medium text-accent-foreground hover:opacity-90"
        >
          Daftar gratis
        </Link>
        <Link
          href="/login"
          className="rounded-md border border-border px-5 py-2.5 font-medium hover:bg-card"
        >
          Masuk
        </Link>
      </div>
    </main>
  );
}
