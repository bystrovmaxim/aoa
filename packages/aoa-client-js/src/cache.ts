// packages/aoa-client-js/src/cache.ts
//
// A small cache for answers already received, so the same question is not asked twice.
//
// Deliberately narrow: an answer is either fresh or gone, there is no size limit, and
// nothing is served while a new answer is fetched. The key is not canonicalised either,
// so the same parameters written in a different order count as a different question and
// miss. Widening any of this is expected to extend this module, not replace it.

import type { ResolveItem, Verdict } from "./types.ts";

export interface CacheEntry {
  operation: string;
  verdict: Verdict;
  fetchedAt: number;
  staleAt: number;
}

// Relies on the caller building `params` with the same key order every time: the key is
// the raw JSON text, so a different order is a different key.
export function cacheKeyFor(cachePartition: string, item: ResolveItem): string {
  return `${cachePartition}::${item.operation}::${JSON.stringify(item.params)}`;
}

// "Could not check" is never cached. It is the absence of a decision, and remembering it
// would keep answering "no" long after whatever broke was fixed.
export function isCacheableVerdict(verdict: Verdict): boolean {
  return verdict.kind !== "FailErrorVerdict";
}

export class ResolveCache {
  private entries = new Map<string, CacheEntry>();

  get(key: string, now: number): CacheEntry | undefined {
    const entry = this.entries.get(key);
    if (!entry || now >= entry.staleAt) return undefined;
    return entry;
  }

  // Answers can arrive out of order, and a slow one must never overwrite a newer answer
  // already recorded -- that would resurrect a permission that has just been revoked.
  // Only a strictly newer entry is protected; everything else writes through.
  set(key: string, entry: CacheEntry): void {
    const existing = this.entries.get(key);
    if (existing && existing.fetchedAt > entry.fetchedAt) return;
    this.entries.set(key, entry);
  }
}
