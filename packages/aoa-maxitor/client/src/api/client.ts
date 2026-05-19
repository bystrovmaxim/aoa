// src/api/client.ts
const configuredApiBaseUrl = import.meta.env.VITE_MAXITOR_API_BASE_URL?.trim() ?? "";

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (!configuredApiBaseUrl) {
    return normalizedPath;
  }
  return `${configuredApiBaseUrl.replace(/\/$/, "")}${normalizedPath}`;
}
