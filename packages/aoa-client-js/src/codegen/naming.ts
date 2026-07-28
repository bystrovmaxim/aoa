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

// Words JavaScript reserves. They cannot name a declaration anywhere, which is stricter
// than the identifier check used elsewhere: as a property key, `delete` is perfectly
// fine. Declarations need their own, stricter list.
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
 * Refuses a name that cannot legally be a TypeScript declaration, before anything is
 * derived from it. Nothing guarantees the server's action name is a legal identifier: a
 * stray space or dot, or an empty name left after stripping the "Action" suffix from
 * something that was only "Action", reaches every name built from it. Adding a number to
 * disambiguate does not repair that -- it produces "2".
 *
 * Failing here, naming the action at fault, beats handing back a file that only fails
 * when somebody tries to compile it.
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
 * Tracks every name the generated file declares, in one shared namespace -- not only the
 * names taken from actions, but the ones derived and lifted out of nested definitions too.
 * Nothing guarantees any of them is unique: the server's action names carry no such
 * promise, and a lifted name is built by gluing strings together.
 *
 * A collision has to be caught here, because it does not fail on its own. TypeScript
 * merges two interfaces that share a name, quietly splicing one action's fields into
 * another.
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
