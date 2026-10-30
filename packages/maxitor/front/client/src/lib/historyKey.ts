// src/lib/historyKey.ts
/**
 * A tab's read keys.
 *
 * A link to a private history carries its key after ``#key=``, which no browser sends to a server. The
 * page keeps the key in this tab's ``sessionStorage`` and leaves it in the address bar, so the address
 * bar is the link to share: copied as it is, it opens the same history at the same version elsewhere
 * (spec 037, FR-010a, the maintainer, 2026-10-30).
 */

import { parseHistory } from "@/lib/historyAddress";
import { getRecent } from "@/lib/serviceUrlHistory";

const PREFIX = "maxitor:historyKey:";

/** Keep ``key`` for the history named ``name``, in this tab only. */
export function rememberKey(name: string, key: string): void {
  try {
    sessionStorage.setItem(PREFIX + name, key);
  } catch {
    // sessionStorage unavailable — the key then lives only in Recent.
  }
}

/** The key this tab holds for ``name``, else the one Recent holds, else ``""``. */
export function keyFor(name: string): string {
  try {
    const held = sessionStorage.getItem(PREFIX + name);
    if (held) return held;
  } catch {
    // fall through to Recent
  }
  for (const record of getRecent()) {
    try {
      const history = parseHistory(record.address);
      if (history?.kind === "private" && history.name === name) return history.key;
    } catch {
      // a record out of shape names no key
    }
  }
  return "";
}

/** Take a ``#key=`` from the page's address and keep it for the history its ``history`` parameter names; the address keeps it too. */
export function adoptKeyFromLocation(): void {
  const { hash, search } = window.location;
  if (!hash.startsWith("#key=")) return;
  const name = new URLSearchParams(search).get("history");
  const key = decodeURIComponent(hash.slice("#key=".length)).trim();
  if (name && key) rememberKey(name, key);
}
