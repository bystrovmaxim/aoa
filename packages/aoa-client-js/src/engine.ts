// packages/aoa-client-js/src/engine.ts
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
  clock?: () => number; // time source; defaults to Date.now (used starting chapter 6's cache)
  // Trace-id generator; defaults to crypto.randomUUID. Injectable for the same
  // reason fetchImpl is: crypto.randomUUID() isn't available identically
  // everywhere (older Node, a non-secure browser context), and this class
  // otherwise promises environment dependencies go through the constructor.
  generateTraceId?: () => string;
}

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

  constructor(config: { transport: TransportConfig }) {
    this.config = config;
  }

  // Opaque subject label, read-only: no setter, identity cannot change.
  // Switching subjects means constructing a new AoaEngine.
  get cachePartition(): string {
    return this.config.transport.cachePartition;
  }

  async resolve(items: ResolveItem[], opts?: { traceId?: string }): Promise<Verdict[]> {
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
}
