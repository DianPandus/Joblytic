import { createClient } from "@/lib/supabase/client";
import { API_URL } from "@/lib/supabase/env";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// Memanggil backend FastAPI dengan access token Supabase pengguna yang sedang login.
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = new Headers(init.headers);
  if (session) headers.set("Authorization", `Bearer ${session.access_token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!res.ok) {
    // statusText selalu kosong di HTTP/2, jadi kode status dipakai sebagai cadangan.
    let detail = res.statusText || `HTTP ${res.status}`;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}
