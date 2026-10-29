// src/lib/historyKey.ts
/**
 * A tab's read keys — kept out of every address the browser keeps.
 *
 * A link Maxitor hands out (**Copy link**, a room's link) carries a private history's key after
 * ``#key=``, which no browser sends to a server. Once the page has read it, the key moves to this
 * tab's ``sessionStorage`` — gone when the tab closes — and the fragment is removed from the address
 * bar without a new history entry, so neither the address bar, nor the browser's history, nor a
 * synced history ever holds it (spec 037, FR-010a). Beyond the tab, a key remains only in Recent.
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

/**
 * Take a ``#key=`` from the page's address: keep it for the history its ``history`` parameter names
 * and take it out of the address bar, replacing the entry rather than adding one.
 */
export function adoptKeyFromLocation(): void {
  const { hash, search, pathname } = window.location;
  if (!hash.startsWith("#key=")) return;
  const name = new URLSearchParams(search).get("history");
  const key = decodeURIComponent(hash.slice("#key=".length)).trim();
  if (name && key) rememberKey(name, key);
  window.history.replaceState(window.history.state, "", `${pathname}${search}`);
}
