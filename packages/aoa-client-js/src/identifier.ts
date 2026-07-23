// packages/aoa-client-js/src/identifier.ts
//
// Shared by both entry points: json-schema-ir.ts (codegen) uses it to decide whether a
// property key needs quoting; path-layout.ts (runtime + codegen) uses it to decide
// whether a path segment can become a dot alias. Kept here, not under codegen/, so the
// runtime entry point (via path-layout.ts) never has to import from the codegen entry.

const VALID_IDENTIFIER = /^[A-Za-z_$][A-Za-z0-9_$]*$/;

export function isValidIdentifier(name: string): boolean {
  return VALID_IDENTIFIER.test(name);
}
