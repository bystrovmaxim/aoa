// packages/aoa-client-js/src/engine.ts
import { cacheKeyFor, isCacheableVerdict, ResolveCache } from "./cache.ts";
import { buildDynamicGateApi, type DynamicGateApi } from "./dynamic-api.ts";
import { assertManifestShape } from "./manifest-types.ts";
import { buildLayout, type LayoutEndpoint } from "./path-layout.ts";
import type { FailErrorVerdict, FailSecurityVerdict, ResolveItem, ResolveResponse, Verdict } from "./types.ts";

// The instance's identity and everything one network call needs. Identity
// (cache_partition) is an opaque label the server hands out on
// authentication -- never in the manifest, never in the resolver response.
export interface TransportConfig {
  baseUrl: string;
  fetchImpl: typeof fetch;
  cachePartition: string; // subject identity; fixed for the AoaEngine's whole lifetime
  credentials?: RequestCredentials; // "include" for cookie sessions
  headers?: Record<string, string>; // shared headers (e.g. Authorization); overrides defaults case-insensitively
  clock?: () => number; // time source; defaults to Date.now
  // Minimal cache config (chapter 5.5, issue #157) -- only ttlMs so far. Chapter 6
  // (#139) is expected to extend this same object (maxStaleMs, maxEntries,
  // onUnavailable), not replace it.
  cache?: { ttlMs?: number };
  // Trace-id generator; defaults to crypto.randomUUID. Injectable for the same
  // reason fetchImpl is: crypto.randomUUID() isn't available identically
  // everywhere (older Node, a non-secure browser context), and this class
  // otherwise promises environment dependencies go through the constructor.
  generateTraceId?: () => string;
}

const DEFAULT_TTL_MS = 3_000;

// Request-level typed failures -- resolve() throws these, never returns them
// as a verdict. Resolver unavailability never turns into a denial. Each sets
// its own `.name` so logging/console output that doesn't do an explicit
// `instanceof` check (the common case) can still tell the four classes apart
// instead of seeing "Error" for all of them.
export class Unauthorized extends Error {
  // 401
  constructor(message: string) {
    super(message);
    this.name = "Unauthorized";
  }
}

export class ProtocolError extends Error {
  // wrong content-type / version / cardinality / malformed body / invalid result element
  constructor(message: string) {
    super(message);
    this.name = "ProtocolError";
  }
}

export class NetworkUnavailable extends Error {
  // fetch itself threw (network down)
  constructor(message: string) {
    super(message);
    this.name = "NetworkUnavailable";
  }
}

// Error for a single question, FailErrorVerdict class. AoaEngine.resolve
// itself never throws this -- it returns a FailErrorVerdict element as-is;
// Primitive.can() (chapter 5) is what throws it. `.message` is a sentence
// (matching the other three classes here), `.reason` is the raw wire code --
// the two carry different meaning, not the same string twice.
export class AoaResolveError extends Error {
  reason: string;

  constructor(reason: string) {
    super(`resolver could not check this operation: ${reason}`);
    this.name = "AoaResolveError";
    this.reason = reason;
  }
}

// The wire only carries a reason string -- whether a retry makes sense is
// entirely a client-side judgment call, the wire has no such concept.
// TIMEOUT is transient, worth retrying. UNKNOWN_ENDPOINT and
// EVALUATION_FAILED are durable configuration/logic failures, retrying
// changes nothing. An unexpected exception's class name (when reason
// doesn't match a known code) is treated the same way: an unplanned failure
// has no basis for being assumed transient.
export function isRetryableCheckError(reason: string): boolean {
  return reason === "TIMEOUT";
}

const KNOWN_VERDICT_KINDS = new Set(["AllowedVerdict", "FailSecurityVerdict", "FailErrorVerdict"]);

// A question without an answer must never be misread as a denial -- an
// element missing `kind`, or carrying one outside the closed set the server
// actually emits, is a broken response, not a permission decision. Checked
// once, here, for every element, the same way `version`/cardinality already
// are -- not left to whatever the caller's own `kind === "AllowedVerdict"`
// check happens to do with `undefined`. The message deliberately doesn't
// echo the element's contents (matches the convention already used
// server-side for a broken access_decide() override): a malformed element
// could carry anything.
function assertValidVerdict(item: unknown, index: number): asserts item is Verdict {
  if (typeof item !== "object" || item === null) {
    throw new ProtocolError(`results[${index}] is not an object`);
  }
  const kind = (item as { kind?: unknown }).kind;
  if (typeof kind !== "string" || !KNOWN_VERDICT_KINDS.has(kind)) {
    throw new ProtocolError(`results[${index}] has an unrecognized kind`);
  }
  if (kind !== "AllowedVerdict") {
    const reason = (item as Partial<FailSecurityVerdict | FailErrorVerdict>).reason;
    if (typeof reason !== "string" || reason.length === 0) {
      throw new ProtocolError(`results[${index}] (${kind}) is missing a non-empty reason`);
    }
  }
}

export class AoaEngine {
  private config: { transport: TransportConfig };
  private cache = new ResolveCache();

  constructor(config: { transport: TransportConfig }) {
    // Validated once, here, rather than on every resolve() call: a NaN ttlMs
    // (e.g. from an unvalidated env var) would make staleAt = now + NaN = NaN,
    // and `now >= NaN` is always false in JS -- the entry would never expire,
    // silently becoming "eternally fresh" (audit finding 8, chapter 5.5).
    const ttlMs = config.transport.cache?.ttlMs;
    if (ttlMs !== undefined && !(Number.isFinite(ttlMs) && ttlMs >= 0)) {
      throw new Error(`transport.cache.ttlMs must be a finite number >= 0, got ${ttlMs}`);
    }
    this.config = config;
  }

  // Opaque subject label, read-only: no setter, identity cannot change.
  // Switching subjects means constructing a new AoaEngine.
  get cachePartition(): string {
    return this.config.transport.cachePartition;
  }

  // Per item: read the cache unless opts.skipCache -- Primitive.run()'s precheck
  // (chapter 5.5) sets it, since a cache hit there would defeat the whole point of a
  // fresh check right before the real invocation. A fresh network answer is written
  // through to the cache regardless of skipCache, so the next ordinary call benefits.
  // Only the actual misses go to the network, in one batched call.
  async resolve(items: ResolveItem[], opts?: { traceId?: string; skipCache?: boolean }): Promise<Verdict[]> {
    const t = this.config.transport;
    const now = (t.clock ?? Date.now)();
    const results: Verdict[] = new Array(items.length);
    const misses: { index: number; item: ResolveItem; key: string }[] = [];

    items.forEach((item, index) => {
      const key = cacheKeyFor(t.cachePartition, item);
      if (!opts?.skipCache) {
        const entry = this.cache.get(key, now);
        if (entry) {
          results[index] = entry.verdict;
          return;
        }
      }
      misses.push({ index, item, key });
    });

    if (misses.length === 0) return results;

    const networkResults = await this.fetchResolve(
      misses.map((m) => m.item),
      opts,
    );
    const ttlMs = t.cache?.ttlMs ?? DEFAULT_TTL_MS;
    misses.forEach((m, i) => {
      const verdict = networkResults[i];
      results[m.index] = verdict;
      if (isCacheableVerdict(verdict)) {
        this.cache.set(m.key, { operation: m.item.operation, verdict, fetchedAt: now, staleAt: now + ttlMs });
      }
    });

    return results;
  }

  // The actual HTTP round-trip -- operates only on whatever subset resolve() didn't
  // already have a fresh cache answer for, so cardinality/index-based validation below
  // is relative to that subset, not necessarily the caller's original full batch.
  private async fetchResolve(items: ResolveItem[], opts?: { traceId?: string }): Promise<Verdict[]> {
    const t = this.config.transport;
    const generateTraceId = t.generateTraceId ?? (() => crypto.randomUUID());
    const traceId = opts?.traceId ?? generateTraceId(); // unique per call unless overridden

    // Headers merge case-insensitively: a caller-supplied `content-type` or
    // `X-Trace-Id` must replace the default, not sit next to it as a second,
    // differently-cased key that fetch then joins with a comma on the wire.
    const headers = new Headers({ "Content-Type": "application/json", "x-trace-id": traceId });
    for (const [key, value] of Object.entries(t.headers ?? {})) {
      headers.set(key, value);
    }

    let res: Response;
    try {
      res = await t.fetchImpl(`${t.baseUrl}/permissions/resolve`, {
        method: "POST",
        credentials: t.credentials,
        headers,
        body: JSON.stringify({ version: 1, items }),
      });
    } catch {
      throw new NetworkUnavailable("resolver unreachable");
    }

    // Validate the response before trusting it.
    if (!res.ok) {
      if (res.status === 401) throw new Unauthorized("not authenticated");
      throw new ProtocolError(`unexpected status ${res.status}`);
    }

    // Compare the media type only -- case-insensitively, and without the
    // parameter section (e.g. `; charset=utf-8`) -- rather than a substring
    // check, which both accepts non-JSON types that merely contain the text
    // "application/json" (e.g. "application/jsonp") and rejects legitimate
    // JSON served with a differently-cased media type.
    const mediaType = res.headers.get("content-type")?.split(";", 1)[0]?.trim().toLowerCase();
    if (mediaType !== "application/json") {
      throw new ProtocolError("response is not application/json");
    }

    let body: unknown;
    try {
      body = await res.json();
    } catch {
      throw new ProtocolError("response body is not valid JSON");
    }
    if (typeof body !== "object" || body === null) {
      throw new ProtocolError("response body is not a JSON object");
    }

    const typedBody = body as ResolveResponse;
    if (typedBody.version !== 1) throw new ProtocolError(`unexpected version ${typedBody.version}`);
    if (!Array.isArray(typedBody.results) || typedBody.results.length !== items.length) {
      throw new ProtocolError("results cardinality does not match items");
    }
    typedBody.results.forEach((item, index) => assertValidVerdict(item, index));
    return typedBody.results;
  }

  // Dynamic mode (chapter 5): fetches the same manifest generateClient reads, but builds
  // the api object in memory instead of writing TypeScript to a file -- no build step,
  // no compile-time per-endpoint types (the manifest's shape is only known once this
  // actually runs). Reuses the exact same manifest -> layout logic as generateClient
  // (path-layout.ts's buildLayout) so the static and dynamic outputs are identical in
  // shape; only how a leaf gets built differs (a real GatePrimitive here, generated
  // source there). Only ever builds the gate (verdict/can) surface -- there is no
  // actionInvoker parameter to build a working .run() from.
  async loadFrom(url: string): Promise<DynamicGateApi> {
    const t = this.config.transport;
    let res: Response;
    try {
      res = await t.fetchImpl(url);
    } catch {
      throw new NetworkUnavailable("manifest unreachable");
    }
    if (!res.ok) {
      throw new ProtocolError(`unexpected status ${res.status} fetching manifest`);
    }
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      throw new ProtocolError("manifest response body is not valid JSON");
    }
    try {
      assertManifestShape(body, url);
    } catch (error) {
      throw new ProtocolError((error as Error).message);
    }
    const layoutEndpoints: LayoutEndpoint[] = body.endpoints.map((endpoint) => ({
      operation: endpoint.operation,
      method: endpoint.route.method,
      path: endpoint.route.path,
      baseName: endpoint.name, // unused by buildLayout/buildDynamicGateApi -- no TS identifiers to name here
    }));
    return buildDynamicGateApi(buildLayout(layoutEndpoints), this);
  }
}
