// packages/aoa-client-js/src/manifest-types.ts
//
// The `GET /client-manifest.json` wire shape (aoa-fastapi-adapter's manifest.py:
// Manifest/ManifestEndpoint/RouteRef/SchemaEntry) — field names and types verified
// directly against that module's pydantic models, not against tutorial prose.
//
// Shared by both entry points: generateClient (codegen) and AoaEngine.loadFrom
// (runtime) both fetch and validate the same manifest shape.

export interface RouteRef {
  method: string;
  path: string;
}

export interface ManifestEndpoint {
  operation: string;
  name: string;
  domain: string;
  description: string;
  route: RouteRef;
  params_schema: Record<string, unknown>;
  result_schema: Record<string, unknown>;
}

export interface SchemaEntry {
  mode: "validation" | "serialization";
  json_schema: Record<string, unknown>;
}

export interface Manifest {
  manifest_version: string;
  version: number;
  manifest_schema_version: number;
  endpoints: ManifestEndpoint[];
  schemas: Record<string, SchemaEntry>;
}

/**
 * Boundary check on fetched, untrusted JSON -- not a full schema validation (still no
 * opinion on `params_schema`/`result_schema`/`json_schema`'s own internal shape, which
 * is the codegen's and `parseRootSchema`'s job, not this one's). It does validate every
 * `endpoints[]` element and `schemas{}` entry, though: both `generateClient` and
 * `AoaEngine.loadFrom` read `endpoint.route.method`/`.path` directly, with no guard of
 * their own, immediately after this assertion returns -- an `asserts value is Manifest`
 * signature is a promise to the compiler that the FULL shape checks out, not just the
 * top level, and before this fix it wasn't honored: a malformed element crashed both
 * callers with a raw, uncaught TypeError instead of the same typed ProtocolError every
 * other kind of "manifest can't be trusted" already produces here (audit finding 8).
 */
export function assertManifestShape(value: unknown, url: string): asserts value is Manifest {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`Manifest fetched from ${url} is not a JSON object`);
  }
  const manifest = value as Record<string, unknown>;
  if (typeof manifest.version !== "number") {
    throw new Error(`Manifest fetched from ${url} is missing a numeric "version"`);
  }
  if (typeof manifest.manifest_version !== "string") {
    throw new Error(`Manifest fetched from ${url} is missing a string "manifest_version"`);
  }
  if (!Array.isArray(manifest.endpoints)) {
    throw new Error(`Manifest fetched from ${url} is missing an "endpoints" array`);
  }
  manifest.endpoints.forEach((endpoint, index) => assertManifestEndpointShape(endpoint, index, url));
  if (typeof manifest.schemas !== "object" || manifest.schemas === null || Array.isArray(manifest.schemas)) {
    throw new Error(`Manifest fetched from ${url} is missing a "schemas" object`);
  }
  Object.entries(manifest.schemas).forEach(([name, entry]) => assertSchemaEntryShape(entry, name, url));
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function assertManifestEndpointShape(value: unknown, index: number, url: string): void {
  const where = `Manifest fetched from ${url}, endpoints[${index}]`;
  if (!isPlainObject(value)) {
    throw new Error(`${where} is not a JSON object`);
  }
  for (const field of ["operation", "name", "domain", "description"] as const) {
    if (typeof value[field] !== "string") {
      throw new Error(`${where} is missing a string "${field}"`);
    }
  }
  if (!isPlainObject(value.route) || typeof value.route.method !== "string" || typeof value.route.path !== "string") {
    throw new Error(`${where} is missing a "route" object with string "method"/"path"`);
  }
  if (!isPlainObject(value.params_schema)) {
    throw new Error(`${where} is missing a "params_schema" object`);
  }
  if (!isPlainObject(value.result_schema)) {
    throw new Error(`${where} is missing a "result_schema" object`);
  }
}

function assertSchemaEntryShape(value: unknown, name: string, url: string): void {
  const where = `Manifest fetched from ${url}, schemas["${name}"]`;
  if (!isPlainObject(value)) {
    throw new Error(`${where} is not a JSON object`);
  }
  if (value.mode !== "validation" && value.mode !== "serialization") {
    throw new Error(`${where} has an unrecognized "mode" (expected "validation" or "serialization")`);
  }
  if (!isPlainObject(value.json_schema)) {
    throw new Error(`${where} is missing a "json_schema" object`);
  }
}
