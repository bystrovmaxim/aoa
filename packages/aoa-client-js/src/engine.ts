// packages/aoa-client-js/src/engine.ts
import type { ResolveItem, ResolveResponse, Verdict } from "./types.ts";

// The instance's identity and everything one network call needs. Identity
// (cache_partition) is an opaque label the server hands out on
// authentication -- never in the manifest, never in the resolver response.
export interface TransportConfig {
  baseUrl: string;
  fetchImpl: typeof fetch;
  cachePartition: string; // subject identity; fixed for the AoaEngine's whole lifetime
  credentials?: RequestCredentials; // "include" for cookie sessions
  headers?: Record<string, string>; // shared headers (e.g. Authorization)
  clock?: () => number; // time source; defaults to Date.now (used starting chapter 6's cache)
}

// Request-level typed failures -- resolve() throws these, never returns them
// as a verdict. Resolver unavailability never turns into a denial.
export class Unauthorized extends Error {} // 401
export class ProtocolError extends Error {} // wrong content-type / version / cardinality
export class NetworkUnavailable extends Error {} // fetch itself threw (network down)

// Error for a single question, FailErrorVerdict class. AoaEngine.resolve
// itself never throws this -- it returns a FailErrorVerdict element as-is;
// Primitive.can() (chapter 5) is what throws it.
export class AoaResolveError extends Error {
  reason: string;

  constructor(reason: string) {
    super(reason);
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

export class AoaEngine {
  private config: { transport: TransportConfig };

  constructor(config: { transport: TransportConfig }) {
    this.config = config;
  }

  // Opaque subject label, read-only: no setter, identity cannot change.
  // Switching subjects means constructing a new AoaEngine.
  get cachePartition(): string {
    return this.config.transport.cachePartition;
  }

  async resolve(items: ResolveItem[], opts?: { traceId?: string }): Promise<Verdict[]> {
    const traceId = opts?.traceId ?? crypto.randomUUID(); // unique per call
    const t = this.config.transport;
    let res: Response;
    try {
      res = await t.fetchImpl(`${t.baseUrl}/permissions/resolve`, {
        method: "POST",
        credentials: t.credentials,
        headers: { "Content-Type": "application/json", "x-trace-id": traceId, ...t.headers },
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
    if (!res.headers.get("content-type")?.includes("application/json")) {
      throw new ProtocolError("response is not application/json");
    }
    const body = (await res.json()) as ResolveResponse;
    if (body.version !== 1) throw new ProtocolError(`unexpected version ${body.version}`);
    if (!Array.isArray(body.results) || body.results.length !== items.length) {
      throw new ProtocolError("results cardinality does not match items");
    }
    return body.results;
  }
}
