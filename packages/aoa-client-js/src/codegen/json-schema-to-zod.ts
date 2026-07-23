// packages/aoa-client-js/src/codegen/json-schema-to-zod.ts
//
// Renders a parsed IR tree (see json-schema-ir.ts) into zod schema source text.
//
// One deliberate exception: `schemas.ResolveResponse` in the manifest carries
// `results: { items: { $ref: "#/$defs/BaseVerdict" } }`, but `$defs.BaseVerdict` is the
// *abstract* base's own published schema — `{ kind: string }` only, no `reason`, no
// per-subclass shape (see access_verdict.py: BaseVerdict is deliberately abstract, one
// flat class per concrete outcome). The manifest does not publish separate schema
// entries for AllowedVerdict/FailSecurityVerdict/FailErrorVerdict, so there is no
// mechanical way to derive the real, concrete discriminated shape from this input alone.
// A `$ref` to a well-known name in WELL_KNOWN_REF_ZOD is therefore substituted with a
// fixed, hand-authored zod schema instead of a literal (and under-specified) translation
// of the manifest's abstract entry — mirroring the same fixed Verdict contract already
// hand-maintained in ../types.ts.

import { CodegenSchemaError, type IrNode, type ParsedSchema } from "./json-schema-ir.ts";

// Single-line by design: this renderer does no indentation-depth tracking (see
// renderZodObject below), so a template with its own baked-in newlines would come out
// misaligned once substituted at an arbitrary nesting depth. A real consuming project's
// own formatter reformats the whole generated file on save/commit regardless.
const WELL_KNOWN_REF_ZOD: Record<string, string> = {
  BaseVerdict:
    'z.discriminatedUnion("kind", [' +
    'z.object({ kind: z.literal("AllowedVerdict") }), ' +
    'z.object({ kind: z.literal("FailSecurityVerdict"), reason: z.string().min(1) }), ' +
    'z.object({ kind: z.literal("FailErrorVerdict"), reason: z.string().min(1) })' +
    "])",
};

export function renderResolveResponseZodSchema(parsed: ParsedSchema): string {
  const expr = zodExpr(parsed.root, parsed.defs);
  return `export const ResolveResponseSchema = ${expr};`;
}

function zodExpr(node: IrNode, defs: Record<string, IrNode>): string {
  switch (node.kind) {
    case "string":
      return "z.string()";
    case "integer":
      return "z.number().int()";
    case "number":
      return "z.number()";
    case "boolean":
      return "z.boolean()";
    case "unknownRecord":
      return "z.record(z.string(), z.unknown())";
    case "array":
      return `z.array(${zodExpr(node.items, defs)})`;
    case "nullable":
      return `${zodExpr(node.inner, defs)}.nullable().optional()`;
    case "enum":
      return `z.enum([${node.values.map((value) => JSON.stringify(value)).join(", ")}])`;
    case "object":
      return renderZodObject(node.properties, defs);
    case "ref": {
      const wellKnown = WELL_KNOWN_REF_ZOD[node.refName];
      if (wellKnown !== undefined) return wellKnown;
      const target = defs[node.refName];
      if (!target) {
        throw new CodegenSchemaError(`Unknown $ref "${node.refName}" (not present in $defs)`);
      }
      return zodExpr(target, defs);
    }
  }
}

function renderZodObject(properties: Array<{ name: string; schema: IrNode }>, defs: Record<string, IrNode>): string {
  if (properties.length === 0) return "z.object({})";
  const fields = properties.map((prop) => `${JSON.stringify(prop.name)}: ${zodExpr(prop.schema, defs)}`).join(", ");
  return `z.object({ ${fields} })`;
}
