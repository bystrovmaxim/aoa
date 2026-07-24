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
 * Tracks every top-level TypeScript declaration name in the generated file — not just
 * endpoint base names, but the full derived and hoisted forms too — in one shared
 * namespace. `ManifestEndpoint.name` is documented as informational only (manifest.py):
 * nothing guarantees it's unique across endpoints, and a name hoisted from a nested
 * `$defs` entry (`${paramsName}${refName}`, see json-schema-to-ts.ts's `resolveRefName`
 * callback) is a mechanical string concatenation with no uniqueness guarantee of its
 * own either. Left unchecked, either kind of collision would silently splice one
 * declaration's fields into an unrelated one via TypeScript's own interface declaration
 * merging (audit finding 2: this used to be entirely invisible, since only bare endpoint
 * base names were tracked, and only against each other — never against an endpoint's
 * own derived `Params`/`Result` names, and never against a hoisted name at all).
 */
export class NameRegistry {
  private readonly ownerByName = new Map<string, string>();

  /**
   * Claims a base endpoint name, together with its own derived `${base}Params`/
   * `${base}Result` forms, in one step — so a candidate is only accepted once all
   * three are simultaneously free (or already owned by this same operation). Callers
   * that reconstruct `${base}Params`/`${base}Result` from the returned base by simple
   * concatenation (api-layout-to-ts.ts) can rely on that reconstruction staying
   * collision-free, since both forms are reserved here before the base is ever handed
   * back.
   */
  claimBase(base: string, operation: string): string {
    let candidate = base;
    let suffix = 2;
    while (!this.canClaimAll(candidate, operation)) {
      candidate = `${base}${suffix}`;
      suffix += 1;
    }
    this.reserve(candidate, operation);
    this.reserve(`${candidate}Params`, operation);
    this.reserve(`${candidate}Result`, operation);
    return candidate;
  }

  /**
   * Claims a single, already-fully-formed declaration name with no derived forms of
   * its own to protect — for a name hoisted from a nested `$defs` entry, which is
   * always a leaf declaration, never itself further suffixed elsewhere in the codegen.
   */
  claimName(name: string, operation: string): string {
    let candidate = name;
    let suffix = 2;
    while (!this.canClaim(candidate, operation)) {
      candidate = `${name}${suffix}`;
      suffix += 1;
    }
    this.reserve(candidate, operation);
    return candidate;
  }

  private canClaimAll(candidate: string, operation: string): boolean {
    return (
      this.canClaim(candidate, operation) &&
      this.canClaim(`${candidate}Params`, operation) &&
      this.canClaim(`${candidate}Result`, operation)
    );
  }

  private canClaim(name: string, operation: string): boolean {
    const owner = this.ownerByName.get(name);
    return owner === undefined || owner === operation;
  }

  private reserve(name: string, operation: string): void {
    this.ownerByName.set(name, operation);
  }
}
