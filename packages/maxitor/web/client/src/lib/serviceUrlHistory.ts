// src/lib/serviceUrlHistory.ts
/**
 * Recent — the addresses this browser opened, newest first, each with what it turned out to be.
 *
 * A record is a running service (one graph) or a history, with its name, its number of versions
 * and whether it has Live (spec 037, FR-012). A private history's record keeps its whole address,
 * key included, in this browser's own storage, so it reopens without the key asked again — an
 * accepted risk the spec names; it is shown with the key as dots and can be removed. Records
 * written before histories (plain strings) read as services.
 */

const KEY = "maxitor:serviceUrlHistory";
const MAX = 10;

/** One address in Recent and what it turned out to be. */
export type RecentRecord = {
  address: string;
  kind: "service" | "history";
  name?: string;
  versions?: number;
  live?: boolean;
};

/** The records Recent holds, newest first; unreadable storage reads as none. */
export function getRecent(): RecentRecord[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.flatMap((item): RecentRecord[] => {
      if (typeof item === "string") return item.trim() ? [{ address: item, kind: "service" }] : [];
      if (item && typeof item === "object" && typeof item.address === "string" && item.address.trim()) {
        return [{ ...item, kind: item.kind === "history" ? "history" : "service" } as RecentRecord];
      }
      return [];
    });
  } catch {
    return [];
  }
}

function save(records: RecentRecord[]): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(records.slice(0, MAX)));
  } catch {
    // localStorage unavailable — silently ignore
  }
}

/** Put ``record`` first, replacing an older record of the same address. */
export function pushRecent(record: RecentRecord): void {
  const address = record.address.trim();
  if (!address) return;
  save([{ ...record, address }, ...getRecent().filter((r) => r.address !== address)]);
}

/** Remove the record of ``address`` — and with it the key it carried. */
export function removeRecent(address: string): void {
  save(getRecent().filter((r) => r.address !== address));
}

/** The address of a running service, recorded as one graph. */
export function pushServiceUrl(url: string): void {
  pushRecent({ address: url, kind: "service" });
}

/** What Recent says a record turned out to be (spec 037, FR-009a's "Recent says"). */
export function describeRecent(record: RecentRecord): string {
  if (record.kind === "service") return "Live service · one graph";
  const versions = record.versions ?? 0;
  if (versions === 0 && !record.live) return `History · ${record.name ?? ""} · no version yet`;
  const counted = `${versions} ${versions === 1 ? "version" : "versions"}`;
  return `History · ${record.name ?? ""} · ${counted}${record.live ? " and Live" : ""}`;
}
