// packages/aoa-client-js/src/codegen/json-schema-to-zod.ts
//
// Renders a parsed IR tree (see json-schema-ir.ts) into zod schema source text.
//
// One deliberate exception: `schemas.ResolveResponse` in the manifest carries
// `results: { items: { $ref: "#/$defs/BaseVerdict" } }`, but `$defs.BaseVerdict` is the
// *abstract* base's own published schema — `{ kind: string }` only, no `reason`, no
// per-subclass shape (see base_verdict.py: BaseVerdict is deliberately abstract, one
// flat class per concrete outcome). The manifest does not publish separate schema
// entries for AllowedVerdict/FailSecurityVerdict/FailErrorVerdict, so there is no
// mechanical way to derive the real, concrete discriminated shape from this input alone.
// A `$ref` to a well-known name in WELL_KNOWN_REF_ZOD is therefore substituted with a
// fixed, hand-authored zod schema instead of a literal (and under-specified) translation
// of the manifest's abstract entry — mirroring the same fixed Verdict contract already
// hand-maintained in ../types.ts.

import { CodegenSchemaError, type AdditionalProperties, type IrNode, type IrProperty, type ParsedSchema } from "./json-schema-ir.ts";

// Single-line by design: this renderer does no indentation-depth tracking (see
// renderZodObject below), so a template with its own baked-in newlines would come out
// misaligned once substituted at an arbitrary nesting depth. A real consuming project's
// own formatter reformats the whole generated file on save/commit regardless.
// strictObject, not object: the server's own model is extra="forbid", and its
// published schema says additionalProperties: false. Plain z.object() STRIPS an
// undeclared key instead of refusing it, which would make the two halves of the
// contract disagree in silence -- Python rejects the response, TypeScript accepts
// a quietly trimmed version of it. An undeclared field on a verdict means the
// server is newer than this client; that is exactly the moment to fail loudly,
// and it cannot strand anyone, because the client is regenerated from the same
// live manifest that would have introduced the field.
// Also note AllowedVerdict: strict is what makes a `reason` on it an error rather
// than a silently dropped key -- success has no reason field AT ALL.
const WELL_KNOWN_REF_ZOD: Record<string, string> = {
  BaseVerdict:
    'z.discriminatedUnion("kind", [' +
    'z.strictObject({ kind: z.literal("AllowedVerdict") }), ' +
    'z.strictObject({ kind: z.literal("FailSecurityVerdict"), reason: z.string().min(1) }), ' +
    'z.strictObject({ kind: z.literal("FailErrorVerdict"), reason: z.string().min(1) })' +
    "])",
};

export function renderResolveResponseZodSchema(parsed: ParsedSchema): string {
  const expr = zodExpr(parsed.root, parsed.defs, new Set());
  return `export const ResolveResponseSchema = ${expr};`;
}

// `renderingRefs` tracks the names currently being rendered. A real cycle means reaching
// the SAME name again before it has finished -- not merely referencing it twice from
// unrelated branches, which is ordinary and must not be mistaken for one. Marked on entry,
// unmarked on exit
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
      // Nullable is about the VALUE -- may it be null. Whether the key may be missing at
      // all is a separate question, answered by `required` below. A field can be both:
      // the key must be there, and its value may be null.
      return `${zodExpr(node.inner, defs, renderingRefs)}.nullable()`;
    case "enum":
      return `z.enum([${node.values.map((value) => JSON.stringify(value)).join(", ")}])`;
    case "object":
      return renderZodObject(node.properties, node.additionalProperties, defs, renderingRefs);
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

function renderZodObject(
  properties: IrProperty[],
  additionalProperties: AdditionalProperties,
  defs: Record<string, IrNode>,
  renderingRefs: Set<string>,
): string {
  // `.passthrough()` keeps extra keys, which zod otherwise strips without saying so. A
  // schema that declares its own properties AND allows extras means both, and both have
  // to survive. The all-extras-and-nothing-declared case never arrives here; it is
  // already resolved to a plain record earlier.
  if (properties.length === 0) return "z.object({})";
  // `required` decides PRESENCE -- may the key be missing -- and nothing about the shape
  // of the value. Confusing the two makes "may be null" quietly mean "may be absent".
  const fields = properties
    .map((prop) => {
      const expr = zodExpr(prop.schema, defs, renderingRefs);
      return `${JSON.stringify(prop.name)}: ${prop.required ? expr : `${expr}.optional()`}`;
    })
    .join(", ");
  // Bare z.object() is neither keep nor refuse: it silently STRIPS, a third
  // behavior no input schema asks for and the one that hides a producer/consumer
  // version mismatch instead of reporting it. So neither branch below emits it.
  //
  // "forbid" is the only refusal. In JSON Schema, saying nothing about extra keys means
  // they are allowed, so an absent setting renders exactly like an explicit yes. Folding
  // it in with "no" instead would reject responses the schema actually permits.
  const object = `z.object({ ${fields} })`;
  return additionalProperties === "forbid" ? `${object}.strict()` : `${object}.passthrough()`;
}
