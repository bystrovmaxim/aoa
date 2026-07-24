// packages/aoa-client-js/src/cache.ts
//
// Minimal cache for AoaEngine.resolve() -- built as a prerequisite for the run()
// precheck's skipCache option (chapter 5.5, issue #157). Chapter 6 (issue #139) owns
// the full freshness/invalidation design (three-timestamp staleAt/hardExpireAt model,
// canonical-JSON keys scoped by cache_partition, maxEntries/LRU, onUnavailable, entity
// tags) and is expected to extend this module rather than replace it. What's here is
// deliberately narrower: a single fresh/stale cutover, no stale-while-revalidate, no
// eviction limit, no canonical JSON -- the key below sorts nothing, so two calls with
// the same params built in a different key order currently miss the cache twice;
// chapter 6 fixes that.

import type { ResolveItem, Verdict } from "./types.ts";

export interface CacheEntry {
  operation: string;
  verdict: Verdict;
  fetchedAt: number;
  staleAt: number;
}

// Not canonical JSON: relies on the caller building `params` with the same key order
// every time. Chapter 6 replaces this with a canonical, cache_partition-scoped key.
export function cacheKeyFor(cachePartition: string, item: ResolveItem): string {
  return `${cachePartition}::${item.operation}::${JSON.stringify(item.params)}`;
}

// FailErrorVerdict is never cached -- it's the absence of a decision (see types.ts's
// own comment on Verdict), not an answer worth remembering.
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

  set(key: string, entry: CacheEntry): void {
    this.entries.set(key, entry);
  }
}
