// Pembacaan FormData untuk Server Action. Pesan ValidationError aman ditampilkan.
export class ValidationError extends Error {}

export function text(form: FormData, name: string, max: number): string | null {
  const value = String(form.get(name) ?? "").trim();
  if (!value) return null;
  if (value.length > max) throw new ValidationError(`Isian "${name}" terlalu panjang.`);
  return value;
}

export function httpUrl(form: FormData, name: string): string | null {
  const value = text(form, name, 2000);
  if (!value) return null;
  try {
    const url = new URL(value);
    if (url.protocol === "http:" || url.protocol === "https:") return url.toString();
  } catch {}
  throw new ValidationError("Tautan harus berupa URL http:// atau https://.");
}

// Satu item per baris; baris kosong dan duplikat (tanpa peduli huruf besar) dibuang.
export function lines(form: FormData, name: string, maxItems: number, maxLength: number): string[] {
  const items: string[] = [];
  const seen = new Set<string>();
  for (const raw of String(form.get(name) ?? "").split("\n")) {
    const item = raw.trim();
    if (!item || seen.has(item.toLowerCase())) continue;
    if (item.length > maxLength) throw new ValidationError(`Ada baris "${name}" yang terlalu panjang.`);
    seen.add(item.toLowerCase());
    items.push(item);
  }
  if (items.length > maxItems) throw new ValidationError(`Isian "${name}" maksimal ${maxItems} baris.`);
  return items;
}
