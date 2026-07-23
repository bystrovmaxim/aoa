// packages/aoa-client-js/src/codegen/naming.ts
//
// Derives TypeScript type names from manifest endpoints. `params_schema`/`result_schema`
// carry no usable name of their own — pydantic's JSON Schema "title" is just the inner
// class's own bare name, almost always the generic "Params"/"Result" for every action in
// this codebase (each action nests `class Params(BaseParams)` / `class Result(BaseResult)`)
// — so names must come from `ManifestEndpoint.name` (the action class name) instead.

const ACTION_SUFFIX = "Action";

/** "CancelOrderAction" -> "CancelOrder"; a name without the suffix is returned as-is. */
export function deriveEndpointBaseName(endpointName: string): string {
  return endpointName.endsWith(ACTION_SUFFIX) && endpointName.length > ACTION_SUFFIX.length
    ? endpointName.slice(0, -ACTION_SUFFIX.length)
    : endpointName;
}

/**
 * Claims a base type name per endpoint. `ManifestEndpoint.name` is documented as
 * informational only (manifest.py) — nothing guarantees it's unique across endpoints —
 * so a second endpoint deriving the same base name gets a deterministic numeric suffix
 * instead of silently colliding with (and shadowing) the first one's generated types.
 */
export class NameRegistry {
  private readonly ownerByBase = new Map<string, string>();

  claimBase(base: string, operation: string): string {
    const owner = this.ownerByBase.get(base);
    if (owner === undefined || owner === operation) {
      this.ownerByBase.set(base, operation);
      return base;
    }
    let suffix = 2;
    while (this.ownerByBase.has(`${base}${suffix}`)) {
      suffix += 1;
    }
    const disambiguated = `${base}${suffix}`;
    this.ownerByBase.set(disambiguated, operation);
    return disambiguated;
  }
}
