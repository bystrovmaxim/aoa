// packages/aoa-client-js/src/codegen/naming.ts
//
// Derives TypeScript type names from manifest endpoints. `params_schema`/`result_schema`
// carry no usable name of their own — pydantic's JSON Schema "title" is just the inner
// class's own bare name, almost always the generic "Params"/"Result" for every action in
// this codebase (each action nests `class Params(BaseParams)` / `class Result(BaseResult)`)
// — so names must come from `ManifestEndpoint.name` (the action class name) instead.

import { isValidIdentifier } from "../identifier.ts";
import { CodegenSchemaError } from "./json-schema-ir.ts";

const ACTION_SUFFIX = "Action";

/** "CancelOrderAction" -> "CancelOrder"; a name without the suffix is returned as-is. */
export function deriveEndpointBaseName(endpointName: string): string {
  return endpointName.endsWith(ACTION_SUFFIX) && endpointName.length > ACTION_SUFFIX.length
    ? endpointName.slice(0, -ACTION_SUFFIX.length)
    : endpointName;
}

// ECMAScript reserved words -- cannot legally name a `const`, `interface`, or `type`
// declaration in ANY position, unlike `isValidIdentifier` (identifier.ts), which
// deliberately allows them for property-key contexts where they're perfectly valid
// (`{ delete: true }`, `path-layout.ts`'s dot-alias segments). Declaration positions
// need this separate, stricter check (audit finding 3).
const RESERVED_WORDS = new Set([
  "break", "case", "catch", "class", "const", "continue", "debugger", "default", "delete",
  "do", "else", "enum", "export", "extends", "false", "finally", "for", "function", "if",
  "import", "in", "instanceof", "new", "null", "return", "super", "switch", "this", "throw",
  "true", "try", "typeof", "var", "void", "while", "with", "yield", "let", "static", "await",
  "implements", "interface", "package", "private", "protected", "public",
]);

export function isReservedWord(name: string): boolean {
  return RESERVED_WORDS.has(name);
}

/**
 * Rejects an endpoint's derived base name at the earliest possible point -- before
 * `NameRegistry.claimBase` ever sees it -- if it isn't a valid, non-reserved TypeScript
 * identifier on its own. `ManifestEndpoint.name` is an arbitrary server-side string with
 * no format guarantee (manifest.py): a stray space/hyphen/dot, or an empty base left
 * over after `deriveEndpointBaseName` strips "Action" from a name that WAS just
 * "Action", reaches every position derived from `base` (`${base}Params`, the
 * SCREAMING_SNAKE descriptor, the lowerFirst local variable) as an invalid identifier a
 * disambiguating numeric suffix cannot repair -- `claimBase("", ...)` on a second
 * collision would happily return the digit-led, still-invalid "2" (audit finding 3).
 * A clear generation-time error naming the offending server action is preferable to a
 * silently-corrupted generated file discovered only once someone tries to compile it.
 */
export function assertValidBaseName(base: string, endpoint: { name: string; operation: string }): void {
  if (isValidIdentifier(base) && !isReservedWord(base)) return;
  throw new CodegenSchemaError(
    `Endpoint "${endpoint.operation}" (server action name "${endpoint.name}") derives ` +
      `${base === "" ? "an empty" : `the invalid`} TypeScript identifier base ${JSON.stringify(base)} ` +
      `-- rename the action so its name, with any trailing "Action" suffix stripped, forms a valid, non-reserved identifier.`,
  );
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
