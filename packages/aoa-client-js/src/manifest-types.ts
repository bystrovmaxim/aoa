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

/** Lightweight boundary check on fetched, untrusted JSON — not a full schema validation. */
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
  if (typeof manifest.schemas !== "object" || manifest.schemas === null || Array.isArray(manifest.schemas)) {
    throw new Error(`Manifest fetched from ${url} is missing a "schemas" object`);
  }
}
