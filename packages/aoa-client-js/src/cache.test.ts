// packages/aoa-client-js/src/cache.test.ts
import { describe, expect, it } from "vitest";

import { cacheKeyFor, isCacheableVerdict, ResolveCache } from "./cache.ts";
import type { CacheEntry } from "./cache.ts";
import type { Verdict } from "./types.ts";

describe("cacheKeyFor", () => {
  it("is deterministic for the same partition, operation, and params", () => {
    const item = { operation: "POST /actions/cancel-order", params: { order_id: 7 } };
    expect(cacheKeyFor("user:1", item)).toBe(cacheKeyFor("user:1", item));
  });

  it("differs when cache_partition differs", () => {
    const item = { operation: "POST /actions/cancel-order", params: { order_id: 7 } };
    expect(cacheKeyFor("user:1", item)).not.toBe(cacheKeyFor("user:2", item));
  });

  it("differs when operation differs", () => {
    const params = { order_id: 7 };
    expect(cacheKeyFor("user:1", { operation: "POST /actions/cancel-order", params })).not.toBe(
      cacheKeyFor("user:1", { operation: "GET /orders", params }),
    );
  });

  it("differs when params differ", () => {
    const operation = "POST /actions/cancel-order";
    expect(cacheKeyFor("user:1", { operation, params: { order_id: 7 } })).not.toBe(
      cacheKeyFor("user:1", { operation, params: { order_id: 8 } }),
    );
  });

  // Documented limitation, not a bug: this key is not canonical JSON. Chapter 6
  // (#139) replaces this with a canonicalized, sorted-key version -- until then, the
  // same question built with a different field order misses the cache twice.
  it("is NOT canonical -- the same params in a different key order currently produce different keys", () => {
    const operation = "POST /actions/cancel-order";
    const a = cacheKeyFor("user:1", { operation, params: { order_id: 7, note: "x" } });
    const b = cacheKeyFor("user:1", { operation, params: { note: "x", order_id: 7 } });
    expect(a).not.toBe(b);
  });
});

describe("isCacheableVerdict", () => {
  it.each<[string, Verdict, boolean]>([
    ["AllowedVerdict", { kind: "AllowedVerdict" }, true],
    ["FailSecurityVerdict", { kind: "FailSecurityVerdict", reason: "no access" }, true],
    ["FailErrorVerdict", { kind: "FailErrorVerdict", reason: "UNKNOWN_ENDPOINT" }, false],
  ])("%s -> %s", (_label, verdict, expected) => {
    expect(isCacheableVerdict(verdict)).toBe(expected);
  });
});

describe("ResolveCache", () => {
  const entry: CacheEntry = { operation: "POST /actions/cancel-order", verdict: { kind: "AllowedVerdict" }, fetchedAt: 0, staleAt: 1_000 };

  it("get() on an empty cache returns undefined", () => {
    const cache = new ResolveCache();
    expect(cache.get("missing-key", 0)).toBeUndefined();
  });

  it("get() returns the entry while still before staleAt", () => {
    const cache = new ResolveCache();
    cache.set("k", entry);
    expect(cache.get("k", 999)).toEqual(entry);
  });

  it("get() treats staleAt itself as already expired, not fresh", () => {
    const cache = new ResolveCache();
    cache.set("k", entry);
    expect(cache.get("k", 1_000)).toBeUndefined();
  });

  it("get() returns undefined well past staleAt", () => {
    const cache = new ResolveCache();
    cache.set("k", entry);
    expect(cache.get("k", 5_000)).toBeUndefined();
  });

  it("set() overwrites a previous entry for the same key when the new one is at least as fresh", () => {
    const cache = new ResolveCache();
    cache.set("k", entry);
    const replacement: CacheEntry = { ...entry, verdict: { kind: "FailSecurityVerdict", reason: "revoked" } };
    cache.set("k", replacement);
    expect(cache.get("k", 0)).toEqual(replacement);
  });

  // Audit finding 2: two resolve() calls to the same key can answer out of
  // order (a slow .can() response landing after a fast run() precheck already
  // wrote a just-revoked denial). Blindly overwriting on every set() would let
  // the older, slower answer roll back the fresher one.
  it("set() refuses to overwrite a strictly newer entry with an older one", () => {
    const cache = new ResolveCache();
    const newer: CacheEntry = {
      operation: "POST /actions/cancel-order",
      verdict: { kind: "FailSecurityVerdict", reason: "revoked" },
      fetchedAt: 10,
      staleAt: 3_010,
    };
    cache.set("k", newer);
    const olderStale: CacheEntry = { operation: "POST /actions/cancel-order", verdict: { kind: "AllowedVerdict" }, fetchedAt: 5, staleAt: 3_005 };
    cache.set("k", olderStale);
    expect(cache.get("k", 10)).toEqual(newer);
  });
});
