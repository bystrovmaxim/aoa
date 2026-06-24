// src/lib/serviceUrlHistory.ts
const KEY = "maxitor:serviceUrlHistory";
const MAX = 10;

export function getServiceUrlHistory(): string[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as string[]).filter((s) => typeof s === "string" && s.trim()) : [];
  } catch {
    return [];
  }
}

export function pushServiceUrl(url: string): void {
  const trimmed = url.trim();
  if (!trimmed) return;
  const history = getServiceUrlHistory().filter((u) => u !== trimmed);
  history.unshift(trimmed);
  try {
    localStorage.setItem(KEY, JSON.stringify(history.slice(0, MAX)));
  } catch {
    // localStorage unavailable — silently ignore
  }
}
