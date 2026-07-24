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

import { CodegenSchemaError, type IrNode, type IrProperty, type ParsedSchema } from "./json-schema-ir.ts";

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
  const expr = zodExpr(parsed.root, parsed.defs, new Set());
  return `export const ResolveResponseSchema = ${expr};`;
}

// `renderingRefs` tracks $defs names currently on the recursion stack -- a real cycle
// (audit finding 7) means calling into the SAME name again before it's finished
// rendering, not merely referencing it twice from unrelated branches (a common,
// legitimate pattern this must not false-positive on). Marked on entry, unmarked on exit
// (`finally`), matching a standard DFS cycle check: the TS renderer's own accidental
// protection (json-schema-to-ts.ts's `typeText`) relies on interfaces being able to
// forward-reference each other by name, which a zod schema -- an eagerly-constructed
// value, not a lazily-resolved type -- cannot do; without an explicit check here, a real
// cycle recurses until the JS call stack overflows with a raw RangeError instead of the
// same clear, typed CodegenSchemaError every other unsupported-input case in this
// codegen already produces.
function zodExpr(node: IrNode, defs: Record<string, IrNode>, renderingRefs: Set<string>): string {
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
      return `z.array(${zodExpr(node.items, defs, renderingRefs)})`;
    case "nullable":
      // Nullable is purely about the VALUE ("can this be null"), never about whether the
      // key itself may be absent -- that's `required`, an orthogonal, property-level
      // concern handled once in renderZodObject below (audit finding 6). A field that's
      // both required AND nullable (Python's `Optional[str]` with no default -- the key
      // must be present, its value may be null) must stay non-optional here.
      return `${zodExpr(node.inner, defs, renderingRefs)}.nullable()`;
    case "enum":
      return `z.enum([${node.values.map((value) => JSON.stringify(value)).join(", ")}])`;
    case "object":
      return renderZodObject(node.properties, defs, renderingRefs);
    case "ref": {
      const wellKnown = WELL_KNOWN_REF_ZOD[node.refName];
      if (wellKnown !== undefined) return wellKnown;
      const target = defs[node.refName];
      if (!target) {
        throw new CodegenSchemaError(`Unknown $ref "${node.refName}" (not present in $defs)`);
      }
      if (renderingRefs.has(node.refName)) {
        throw new CodegenSchemaError(
          `Cyclic $ref detected at "${node.refName}" -- recursive schemas are not supported by this codegen.`,
        );
      }
      renderingRefs.add(node.refName);
      try {
        return zodExpr(target, defs, renderingRefs);
      } finally {
        renderingRefs.delete(node.refName);
      }
    }
  }
}

function renderZodObject(properties: IrProperty[], defs: Record<string, IrNode>, renderingRefs: Set<string>): string {
  if (properties.length === 0) return "z.object({})";
  // `required` decides PRESENCE (can the key be missing), independent of the value's own
  // form -- the same separation json-schema-to-ts.ts already makes via its own `?` (audit
  // finding 6: this renderer used to ignore `required` entirely, and separately had
  // `nullable` add `.optional()` unconditionally, which is a presence claim disguised as
  // a value-shape one).
  const fields = properties
    .map((prop) => {
      const expr = zodExpr(prop.schema, defs, renderingRefs);
      return `${JSON.stringify(prop.name)}: ${prop.required ? expr : `${expr}.optional()`}`;
    })
    .join(", ");
  return `z.object({ ${fields} })`;
}
