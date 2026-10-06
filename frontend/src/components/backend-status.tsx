"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";

type State =
  | { kind: "connecting"; slow: boolean }
  | { kind: "ok"; role: string }
  | { kind: "error"; message: string };

// Backend free tier di Render tidur setelah 15 menit dan butuh ~1 menit untuk bangun,
// jadi tampilkan status menghubungkan yang jelas alih-alih terlihat rusak.
export function BackendStatus() {
  const [state, setState] = useState<State>({ kind: "connecting", slow: false });

  const connect = useCallback(async () => {
    setState({ kind: "connecting", slow: false });
    const slowTimer = setTimeout(() => setState({ kind: "connecting", slow: true }), 4000);
    try {
      const me = await apiFetch<{ profile: { role: string } }>("/me");
      setState({ kind: "ok", role: me.profile.role });
    } catch (e) {
      setState({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    } finally {
      clearTimeout(slowTimer);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- memulai koneksi saat mount
    connect();
  }, [connect]);

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <h2 className="text-sm font-medium text-muted">Server API</h2>
      {state.kind === "connecting" && (
        <p className="mt-2 text-sm">
          Menghubungkan ke server…
          {state.slow && (
            <span className="block text-muted">
              Server sedang bangun dari mode tidur, biasanya kurang dari satu menit.
            </span>
          )}
        </p>
      )}
      {state.kind === "ok" && (
        <p className="mt-2 text-sm">
          <span className="text-accent">● Terhubung</span>
          <span className="block text-muted">Token terverifikasi, peran: {state.role}</span>
        </p>
      )}
      {state.kind === "error" && (
        <div className="mt-2 text-sm">
          <p className="text-danger">Gagal terhubung: {state.message}</p>
          <button onClick={connect} className="mt-2 text-accent underline">
            Coba lagi
          </button>
        </div>
      )}
    </div>
  );
}
