// Hanya izinkan redirect ke path internal; tolak "//host" dan "/\host" (open redirect).
export function safeNext(next: string | null, fallback = "/dashboard"): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.startsWith("/\\")) {
    return fallback;
  }
  return next;
}
