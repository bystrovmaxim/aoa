// packages/aoa-client-js/src/codegen/generate-client.ts
//
// generateClient(url) — the static codegen entry point (chapter 5). Fetches
// GET /client-manifest.json and returns a self-contained TypeScript source string: one
// Params/Result interface pair per endpoint, the GateApi/CallableApi facades over them
// (hybrid path/dot-alias layout, see path-layout.ts), and the wire-contract zod
// validator ResolveResponseSchema. The three Verdict outcome types are re-exported from
// the runtime package rather than redeclared here — the manifest's own BaseVerdict entry
// is deliberately abstract (kind only, see json-schema-to-zod.ts), so there is no schema
// data to mechanically regenerate FailSecurityVerdict/FailErrorVerdict's `reason` field
// from, and redeclaring a second, hand-maintained copy would be exactly the kind of
// dual-source-of-truth this whole chapter exists to avoid.

import { assertManifestShape, type Manifest, type ManifestEndpoint } from "../manifest-types.ts";
import { parseRootSchema } from "./json-schema-ir.ts";
import { renderParamsOrResultInterface } from "./json-schema-to-ts.ts";
import { renderResolveResponseZodSchema } from "./json-schema-to-zod.ts";
import { NameRegistry, assertValidBaseName, deriveEndpointBaseName } from "./naming.ts";
import { renderApiLayout } from "./api-layout-to-ts.ts";
import { buildLayout, type LayoutEndpoint } from "../path-layout.ts";

export async function generateClient(url: string): Promise<string> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Failed to fetch manifest from ${url}: HTTP ${res.status} ${res.statusText}`);
  }
  const body: unknown = await res.json();
  assertManifestShape(body, url);
  return renderClientSource(body, url);
}

function renderClientSource(manifest: Manifest, url: string): string {
  const registry = new NameRegistry();
  const rendered = manifest.endpoints.map((endpoint) => renderEndpointTypes(endpoint, registry));
  const endpointBlocks = rendered.map((r) => r.source);
  const layoutEndpoints: LayoutEndpoint[] = rendered.map((r) => r.layoutEndpoint);

  const { typesSource, factoriesSource } = renderApiLayout(buildLayout(layoutEndpoints));

  const resolveResponseEntry = manifest.schemas.ResolveResponse;
  if (!resolveResponseEntry) {
    throw new Error(`Manifest fetched from ${url} is missing the required "schemas.ResolveResponse" entry`);
  }
  const parsedResolveResponse = parseRootSchema(resolveResponseEntry.json_schema, "schemas.ResolveResponse");
  const zodBlock = [
    '// Wire contract validator — generated from the manifest\'s "schemas.ResolveResponse" entry.',
    renderResolveResponseZodSchema(parsedResolveResponse),
  ].join("\n");

  const sections = [renderHeader(url, manifest), renderImports(), ...endpointBlocks, typesSource, factoriesSource, zodBlock];
  return `${sections.join("\n\n")}\n`;
}

function renderEndpointTypes(endpoint: ManifestEndpoint, registry: NameRegistry): { source: string; layoutEndpoint: LayoutEndpoint } {
  const rawBase = deriveEndpointBaseName(endpoint.name);
  // Reject an invalid or empty base before it ever reaches the registry (audit finding
  // 3) -- claimBase's numeric-suffix disambiguation exists to resolve a collision
  // between two otherwise-valid names, not to repair a base that was never a valid
  // identifier to begin with (an empty base disambiguated against itself becomes the
  // digit-led, still-invalid "2").
  assertValidBaseName(rawBase, endpoint);
  const base = registry.claimBase(rawBase, endpoint.operation);
  const paramsName = `${base}Params`;
  const resultName = `${base}Result`;

  const parsedParams = parseRootSchema(endpoint.params_schema, `${endpoint.operation} params_schema`);
  const parsedResult = parseRootSchema(endpoint.result_schema, `${endpoint.operation} result_schema`);

  // A name hoisted from a nested $defs entry is a mechanical string concatenation with
  // no uniqueness guarantee of its own (audit finding 2) -- claiming it through the same
  // registry as endpoint base names guarantees it can't collide with (and, via
  // TypeScript's own interface declaration merging, silently corrupt) another endpoint's
  // own top-level Params/Result interface, or another hoisted name from elsewhere in the
  // file. Idempotent for the same (name, operation) pair, so re-hoisting the same $ref
  // twice within one endpoint's own interface still resolves to the same name.
  const paramsSource = renderParamsOrResultInterface(paramsName, parsedParams, (ref) =>
    registry.claimName(`${paramsName}${ref}`, endpoint.operation),
  );
  const resultSource = renderParamsOrResultInterface(resultName, parsedResult, (ref) =>
    registry.claimName(`${resultName}${ref}`, endpoint.operation),
  );

  return {
    source: [`// ${endpoint.operation}`, paramsSource, "", resultSource].join("\n"),
    layoutEndpoint: { operation: endpoint.operation, method: endpoint.route.method, path: endpoint.route.path, baseName: base },
  };
}

function renderHeader(url: string, manifest: Manifest): string {
  return [
    "// AUTO-GENERATED by aoa-client-js/codegen — DO NOT EDIT BY HAND.",
    `// Source: ${url}`,
    `// Manifest version: ${manifest.manifest_version}`,
  ].join("\n");
}

function renderImports(): string {
  return [
    'import { z } from "zod";',
    'import { makeCallablePrimitive, makeGatePrimitive } from "aoa-client-js";',
    'import type { ActionInvoker, AoaEngine, CallablePrimitive, GatePrimitive } from "aoa-client-js";',
    'export type { AllowedVerdict, FailErrorVerdict, FailSecurityVerdict, Verdict } from "aoa-client-js";',
  ].join("\n");
}
